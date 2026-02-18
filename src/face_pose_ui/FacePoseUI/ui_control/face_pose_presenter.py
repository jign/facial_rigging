from typing import Optional, List
import pymel.core as pm
from FacePoseUI.core.rig import Rig
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose
from FacePoseUI.ui.select_driver_dialog import SelectDriverDialog
from FacePoseUI.ui.set_driven_objs_dialog import SetDrivenObjsDialog
from FacePoseUI.ui.add_attrs_to_driver_dialog import AddAttrsToDriverDialog
from FacePoseUI.ui.new_pose_dialog import NewPoseDialog
from FacePoseUI.core.serialization.rig_serializer import RigSerializer, RigDeserializer
import FacePoseUI.ui_control.capture_context as captc
import FacePoseUI.ui_control.pose_context as posec
import FacePoseUI.ui_control.mirror_context as mirc
import FacePoseUI.core.core_tools as ct
from pathlib import Path


class FacePosePresenter:
    def __init__(self):
        self.rig: Optional[Rig] = None
        self.view = None  # Will be set by the view

        self.selected_pose: Optional[Pose] = None
        self.selected_subpose: Optional[Subpose] = None

    def set_view(self, view):
        self.view = view  
        
    def set_driver(self):
        """
        Sets the rig driver by displaying a selection dialog and updates the UI.
        This method opens a dialog to let the user select a driver, creates a new Rig instance
        with the selected driver, updates the driver display in the view, and refreshes the UI.
        Returns:
            None
        """
        selected_driver = SelectDriverDialog.get_driver()
        self.rig = Rig(selected_driver)
        self.view.update_driver_display(selected_driver.getName())
        self.refresh_ui()

    def get_selected_pose(self) -> Optional[Pose]:
        return self.selected_pose
    
    def get_selected_subpose(self) -> Optional[Subpose]:
        if self.selected_pose is None:
            return None
        return self.selected_subpose
    
    def get_subposes(self) -> List[Subpose]:
        selected_pose = self.get_selected_pose()
        if selected_pose is None:
            return []
        return selected_pose.subposes
    
    def refresh_ui(self):
        """Refreshes all UI elements based on the current state"""
        if self.rig is None:
            return
            
        # Store Maya selection state
        current_maya_selection = pm.selected()
            
        current_pose = self.get_selected_pose()
        current_subpose = self.get_selected_subpose()
        
        # Refresh the view (pass the data to the view)
        # TODO get driven objects shouldn't be here maybe?
        self.view.refresh_attrs_in_driver(ct.get_driven_objs_for_driver(self.rig.driver))
        self.refresh_poses()
        
        # Restore selections
        if current_pose:
            self.view.select_pose(current_pose)
            self.refresh_subposes()
            
            if current_subpose:
                self.view.select_subpose(current_subpose)
                self.refresh_keys_spreadsheet(current_subpose)
        
        # Restore Maya selection at the end
        if current_maya_selection:
            pm.select(current_maya_selection, replace=True)
    
    def refresh_poses(self):
        """Refresh the pose list"""
        if self.rig:
            self.view.refresh_pose_list(self.rig.get_poses())
    
    def refresh_subposes(self):
        """Refresh the subpose list for current pose"""
        if self.rig:
            self.view.refresh_subpose_list(self.get_subposes())

    def refresh_attrs_in_driver(self):
        """Refresh the attributes in driver tree"""
        if self.rig:
            self.view.refresh_attrs_in_driver(ct.get_driven_objs_for_driver(self.rig.driver))
            self.refresh_subposes()

    def refresh_keys_spreadsheet(self, subpose):
        """Update the keys spreadsheet with the given subpose data"""
        if subpose:
            self.view.refresh_keys_spreadsheet(subpose)
        else:
            self.view.clear_keys_spreadsheet()
    
    def add_subposes(self, attrs):
        """Add subposes for the given attributes"""
        if self.rig:
            # Store the currently selected pose before making changes
            current_pose = self.get_selected_pose()

            posec.add_subposes_to_pose(self.rig, current_pose, attrs)

            self.refresh_ui()

            # If we had a pose selected but it got deselected during refresh,
            # explicitly reselect it and ensure the UI reflects this selection
            if current_pose is not None and self.get_selected_pose() != current_pose:
                self.on_pose_selected(current_pose)
    
    def add_subposes_from_dialog(self):
        """
        Opens a non-modal dialog to get attributes for subposes.
        
        The dialog allows the user to select Maya objects while it's open.
        When attributes are selected and confirmed, they're added to the rig
        and the UI is refreshed.
        """
        def on_attrs_selected(attrs):
            if attrs:  # Only process if we received attributes
                self.add_subposes(attrs)
                
        # Get a function that will create our dialog with the callback
        create_dialog = SetDrivenObjsDialog.get_attrs(parent=self.view)
        # Create the dialog passing our callback
        create_dialog(on_attrs_selected)

    def add_attrs_to_driver(self):
        """
        Adds attributes from a selected object to the rig driver.

        This method performs the following steps:
        1. Gets the currently selected Maya object (if any)
        2. Opens a dialog to let the user choose which attributes to add
        3. Adds the selected attributes to the rig
        4. Refreshes the UI to display the updated attributes

        Returns:
            None
        """
        selected_obj = pm.selected()[0] if pm.ls(sl=True) else None
        if selected_obj:
            attrs = AddAttrsToDriverDialog.get_attrs(selected_obj, parent=self.view)
            self.add_attrs_to_rig(attrs)
            self.refresh_attrs_in_driver()        
    
    def add_attrs_to_rig(self, attrs):
        if self.rig:
            posec.add_attrs_to_rig(self.rig, attrs)
            self.refresh_attrs_in_driver()

    def delete_current_pose(self):
        """Delete the currently selected pose"""
        selected_pose = self.get_selected_pose()
        if self.rig and selected_pose:
            posec.del_poses(self.rig, selected_pose)
            self.refresh_ui()
    
    def delete_current_subpose(self):
        """Delete the currently selected subpose"""
        selected_subpose = self.get_selected_subpose()
        if self.rig and selected_subpose:
            posec.del_subposes(self.rig, self.get_selected_pose(), selected_subpose)
            self.on_subpose_selected(None)
            self.refresh_ui()
    
    def capture_selected(self):
        """Capture pose values from selected objects"""
        if self.rig:
            current_pose = self.get_selected_pose()
            if current_pose is None:
                print('no pose selected')
                return
                
            captc.capture_selected_objects(current_pose)
            
            # Refresh keys display if a subpose is selected
            current_subpose = self.get_selected_subpose()
            if current_subpose:
                self.refresh_keys_spreadsheet(current_subpose)
    
    def capture_pose(self):
        """Capture all pose values"""
        if self.rig:
            selected_pose = self.get_selected_pose()
            if selected_pose is None:
                print('no pose selected')
                return
                
            captc.capture_pose(selected_pose)
            
            # Refresh keys display if a subpose is selected
            selected_subpose = self.get_selected_subpose()
            if selected_subpose:
                self.refresh_keys_spreadsheet(selected_subpose)
    
    def capture_key(self):
        if self.rig:
            selected_pose = self.get_selected_pose()
            selected_subpose = self.get_selected_subpose()
            if selected_pose is None or selected_subpose is None:
                print('no pose or subpose selected')
                return
                
            captc.capture_key_for_subpose(selected_pose, selected_subpose)
            self.refresh_keys_spreadsheet(selected_subpose)
    
    def delete_key(self, key_idx):
        """Delete a key at the given index"""
        if self.rig:
            selected_pose = self.get_selected_pose()
            selected_subpose = self.get_selected_subpose()
            if selected_pose is None or selected_subpose is None:
                print('no pose selected')
                return
                
            if captc.del_key_for_subpose(selected_pose, selected_subpose, key_idx):
                self.refresh_ui()

    def try_update_key_weight(self, key_idx, new_val):
        selected_subpose = self.get_selected_subpose()
        return captc.try_update_key_weight(selected_subpose, key_idx, new_val)
    
    def try_update_key_value(self, key_idx, new_val):
        selected_subpose = self.get_selected_subpose()
        return captc.try_update_key_value(selected_subpose, key_idx, new_val)
    
    def new_pose(self):
        dialog = NewPoseDialog(self.view, self.rig)
        dialog.exec_()
        self.refresh_ui()
    
    def mirror_current_pose(self):
        """Mirror the currently selected pose"""
        selected_pose = self.get_selected_pose()
        if self.rig and selected_pose:
            mirc.mirror_pose(self.rig, selected_pose)
            self.refresh_ui()
    
    def on_pose_selected(self, pose):
        if self.rig:
            # Get previously selected pose for deselection handling
            previous_pose = self.get_selected_pose()
            
            # If we're selecting a different pose, handle deselection
            if previous_pose is not None and previous_pose != pose:
                self.on_pose_deselected(previous_pose)
            
            self.selected_pose = pose
            self.refresh_subposes()
    
    def on_pose_deselected(self, pose):
        """Handle pose deselection"""
        if self.rig:
            self.selected_subpose = None
            self.view.clear_keys_spreadsheet()
    
    def on_subpose_selected(self, subpose):
        """Handle subpose selection"""
        if self.rig:
            self.selected_subpose = subpose
            self.refresh_keys_spreadsheet(subpose)

    def on_scene_changed(self):
        if self.rig is not None:
            self.refresh_ui()

    def open_blendshapes_win(self):
        """Opens the corrective blendshapes management dialog"""
        if self.rig:
            from FacePoseUI.ui.corrective_blendshapes_dialog import CorrectiveBlendshapesDialog
            dialog = CorrectiveBlendshapesDialog(self.rig, parent=self.view)
            dialog.show()
        else:
            pm.warning("Please select a driver node first")

    def serialize_rig(self, path: Path):
        """Serialize the rig to a file"""
        if self.rig:
            serializer = RigSerializer(path, self.rig)
            serializer.serialize_rig()
    
    def deserialize_rig(self, path: Path):
        """Deserialize the rig from a file"""
        if not self.rig:
            self.rig = Rig(None)
            
        deserializer = RigDeserializer(path, self.rig)
        if self.rig.driver:
            deserializer.load_rig()
        else:
            print('rebuild')
            deserializer.rebuild_rig()
            self.view.update_driver_display(self.rig.driver.getName())
        self.refresh_ui()