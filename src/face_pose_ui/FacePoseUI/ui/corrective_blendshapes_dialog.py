# New file: ui/corrective_blendshapes_dialog.py
import pymel.core as pm
from PySide2 import QtCore, QtWidgets
import skylib.utils.module_utils as smu
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.rig import Rig

class CorrectiveBlendshapesDialog(QtWidgets.QDialog):
    def __init__(self, rig: Rig, parent=smu.get_maya_main_win()):
        super(CorrectiveBlendshapesDialog, self).__init__(parent)
        self.rig = rig
        
        self.setWindowTitle("Corrective Blendshapes Manager")
        self.resize(800, 500)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Window)
        
        self.create_widgets()
        self.create_layouts()
        self.create_connections()
        
        self.refresh_all()
        
    def create_widgets(self):
        # Available poses list
        self.poses_list = QtWidgets.QListWidget()
        self.poses_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.poses_label = QtWidgets.QLabel("Available Poses:")
        
        # Controlling poses for current blendshape
        self.controlling_poses_list = QtWidgets.QListWidget()
        self.controlling_poses_label = QtWidgets.QLabel("Poses driving selected blendshape:")
        
        # Blendshapes list
        self.blendshapes_list = QtWidgets.QListWidget()
        self.blendshapes_label = QtWidgets.QLabel("Corrective Blendshapes:")
        
        # Transfer buttons
        self.add_poses_to_blendshape_btn = QtWidgets.QPushButton("->")
        self.add_poses_to_blendshape_btn.setToolTip("Add selected poses to drive selected blendshape")
        self.remove_poses_from_blendshape_btn = QtWidgets.QPushButton("<-")
        self.remove_poses_from_blendshape_btn.setToolTip("Remove selected poses from blendshape")
        
        # Blendshape management buttons
        self.create_blendshape_btn = QtWidgets.QPushButton("Create New Blendshape")
        self.delete_blendshape_btn = QtWidgets.QPushButton("Delete Blendshape")
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        
    def create_layouts(self):
        # Poses list
        poses_layout = QtWidgets.QVBoxLayout()
        poses_layout.addWidget(self.poses_label)
        poses_layout.addWidget(self.poses_list)
        
        # Transfer buttons
        transfer_buttons_layout = QtWidgets.QVBoxLayout()
        transfer_buttons_layout.addStretch()
        transfer_buttons_layout.addWidget(self.add_poses_to_blendshape_btn)
        transfer_buttons_layout.addWidget(self.remove_poses_from_blendshape_btn)
        transfer_buttons_layout.addStretch()
        
        # Controlling poses list
        controlling_poses_layout = QtWidgets.QVBoxLayout()
        controlling_poses_layout.addWidget(self.controlling_poses_label)
        controlling_poses_layout.addWidget(self.controlling_poses_list)
        
        # Blendshapes list
        blendshapes_layout = QtWidgets.QVBoxLayout()
        blendshapes_layout.addWidget(self.blendshapes_label)
        blendshapes_layout.addWidget(self.blendshapes_list)
        
        # Blendshape buttons
        blendshape_buttons_layout = QtWidgets.QHBoxLayout()
        blendshape_buttons_layout.addWidget(self.create_blendshape_btn)
        blendshape_buttons_layout.addWidget(self.delete_blendshape_btn)
        blendshape_buttons_layout.addWidget(self.refresh_btn)
        
        # Combined left side
        left_layout = QtWidgets.QHBoxLayout()
        left_layout.addLayout(poses_layout)
        left_layout.addLayout(transfer_buttons_layout)
        left_layout.addLayout(controlling_poses_layout)
        
        # Main layout
        main_layout = QtWidgets.QVBoxLayout(self)
        
        lists_layout = QtWidgets.QHBoxLayout()
        lists_layout.addLayout(left_layout, 2)
        lists_layout.addLayout(blendshapes_layout, 1)
        
        main_layout.addLayout(lists_layout)
        main_layout.addLayout(blendshape_buttons_layout)
        
    def create_connections(self):
        self.add_poses_to_blendshape_btn.clicked.connect(self.add_poses_to_blendshape)
        self.remove_poses_from_blendshape_btn.clicked.connect(self.remove_poses_from_blendshape)
        self.create_blendshape_btn.clicked.connect(self.create_blendshape)
        self.delete_blendshape_btn.clicked.connect(self.delete_blendshape)
        self.refresh_btn.clicked.connect(self.refresh_all)
        self.blendshapes_list.itemSelectionChanged.connect(self.on_blendshape_selected)
        
    def refresh_all(self):
        self.refresh_poses_list()
        self.refresh_blendshapes_list()
        
    def refresh_poses_list(self):
        """Fill the poses list with all available poses from the rig"""
        self.poses_list.clear()
        if not self.rig:
            return
            
        for pose in self.rig.get_poses():
            item = QtWidgets.QListWidgetItem(pose.get_pose_name())
            item.setData(QtCore.Qt.UserRole, pose)
            self.poses_list.addItem(item)
            
    def refresh_blendshapes_list(self):
        """Fill the blendshapes list with corrective outputs from the rig driver"""
        self.blendshapes_list.clear()
        if not self.rig or not self.rig.driver:
            return
            
        # Get corrective outputs from the driver node
        try:
            corrective_outputs = self.rig.driver.attr('correctiveOutputs').elements()
            for i, output in enumerate(corrective_outputs):
                # Create a display name - might want to customize this
                name = f"Corrective_{i}"
                
                # Try to get target blendshape name if connected
                if output.isConnected():
                    target = output.outputs(p=True)
                    if target:
                        name = f"{target[0].name().split('.')[-1]} ({i})"
                
                item = QtWidgets.QListWidgetItem(name)
                item.setData(QtCore.Qt.UserRole, i)  # Store the index
                self.blendshapes_list.addItem(item)
        except:
            # Handle if attributes don't exist
            pass
            
    def on_blendshape_selected(self):
        """When a blendshape is selected, update the controlling poses list"""
        self.refresh_controlling_poses_list()
        
    def refresh_controlling_poses_list(self):
        """Show which poses are driving the selected blendshape"""
        self.controlling_poses_list.clear()
        
        selected_items = self.blendshapes_list.selectedItems()
        if not selected_items or not self.rig or not self.rig.driver:
            return
            
        blendshape_idx = selected_items[0].data(QtCore.Qt.UserRole)
        
        # Get poses driving this corrective
        try:
            inputs_plug = self.rig.driver.attr(f'correctiveInputs[{blendshape_idx}]')
            pose_inputs = inputs_plug.attr('correctiveInputPose').elements()
            
            for pose_input in pose_inputs:
                if pose_input.isConnected():
                    source_attr = pose_input.inputs(p=True)[0]
                    # Find the pose object that corresponds to this attribute
                    for pose in self.rig.get_poses():
                        if pose.pose_attr == source_attr:
                            item = QtWidgets.QListWidgetItem(pose.get_pose_name())
                            item.setData(QtCore.Qt.UserRole, pose)
                            self.controlling_poses_list.addItem(item)
                            break
        except:
            # Handle if attributes don't exist
            pass
            
    def add_poses_to_blendshape(self):
        """Add selected poses to drive the selected blendshape"""
        selected_poses = [item.data(QtCore.Qt.UserRole) for item in self.poses_list.selectedItems()]
        selected_blendshape_items = self.blendshapes_list.selectedItems()
        
        if not selected_poses or not selected_blendshape_items or not self.rig or not self.rig.driver:
            return
            
        blendshape_idx = selected_blendshape_items[0].data(QtCore.Qt.UserRole)
        
        # Connect selected poses to the corrective input
        for pose in selected_poses:
            # Find next available index in correctiveInputPose array
            try:
                input_plug = self.rig.driver.attr(f'correctiveInputs[{blendshape_idx}]')
                next_idx = len(input_plug.attr('correctiveInputPose').elements())
                pose_input = input_plug.attr(f'correctiveInputPose[{next_idx}]')
                pose.pose_attr.connect(pose_input)
            except Exception as e:
                pm.warning(f"Failed to connect pose: {e}")
                
        # Refresh the UI
        self.refresh_controlling_poses_list()
        
    def remove_poses_from_blendshape(self):
        """Remove selected poses from the current blendshape"""
        selected_poses = [item.data(QtCore.Qt.UserRole) for item in self.controlling_poses_list.selectedItems()]
        selected_blendshape_items = self.blendshapes_list.selectedItems()
        
        if not selected_poses or not selected_blendshape_items or not self.rig or not self.rig.driver:
            return
            
        blendshape_idx = selected_blendshape_items[0].data(QtCore.Qt.UserRole)
        
        # Disconnect selected poses from the corrective input
        for pose in selected_poses:
            try:
                input_plug = self.rig.driver.attr(f'correctiveInputs[{blendshape_idx}]')
                pose_inputs = input_plug.attr('correctiveInputPose').elements()
                
                for pose_input in pose_inputs:
                    if pose_input.isConnected() and pose_input.inputs(p=True)[0] == pose.pose_attr:
                        pose_input.disconnect()
            except Exception as e:
                pm.warning(f"Failed to disconnect pose: {e}")
                
        # Refresh the UI
        self.refresh_controlling_poses_list()
        
    def create_blendshape(self):
        """Create a new corrective blendshape"""
        if not self.rig or not self.rig.driver:
            return
            
        # Find next available index for correctiveOutputs and add an element
        try:
            next_idx = len(self.rig.driver.attr('correctiveOutputs').elements())
            # Create a new input compound element
            input_plug = self.rig.driver.attr(f'correctiveInputs[{next_idx}]')
            # Make sure output exists too (should be created automatically)
            output_plug = self.rig.driver.attr(f'correctiveOutputs[{next_idx}]')
            
            # Open dialog to connect to a blendshape target
            result = pm.confirmDialog(
                title='Connect Blendshape',
                message='Select a blendshape target, then click Connect',
                button=['Connect', 'Cancel'],
                defaultButton='Connect',
                cancelButton='Cancel',
                dismissString='Cancel'
            )
            
            if result == 'Connect':
                selection = pm.ls(sl=True)
                if selection and isinstance(selection[0], pm.nodetypes.BlendShape):
                    # Get target weight attributes
                    blend_shape = selection[0]
                    # Let user select from a list of targets
                    targets = pm.listAttr(blend_shape + '.w', multi=True)
                    if targets:
                        target = pm.confirmDialog(
                            title='Select Target', 
                            message='Select blendshape target',
                            button=targets,
                            defaultButton=targets[0]
                        )
                        if target in targets:
                            # Connect the output to the selected target
                            output_plug.connect(blend_shape.attr(target))
                
            # Refresh the UI
            self.refresh_blendshapes_list()
            
        except Exception as e:
            pm.warning(f"Failed to create corrective blendshape: {e}")
            
    def delete_blendshape(self):
        """Delete the selected corrective blendshape"""
        selected_items = self.blendshapes_list.selectedItems()
        if not selected_items or not self.rig or not self.rig.driver:
            return
            
        blendshape_idx = selected_items[0].data(QtCore.Qt.UserRole)
        
        # Confirm deletion
        result = pm.confirmDialog(
            title='Delete Corrective',
            message=f'Delete corrective blendshape {selected_items[0].text()}?',
            button=['Yes', 'No'],
            defaultButton='No',
            cancelButton='No',
            dismissString='No'
        )
        
        if result == 'Yes':
            try:
                # Disconnect any connections
                output_plug = self.rig.driver.attr(f'correctiveOutputs[{blendshape_idx}]')
                if output_plug.isConnected():
                    output_plug.disconnect()
                    
                input_plug = self.rig.driver.attr(f'correctiveInputs[{blendshape_idx}]')
                pose_inputs = input_plug.attr('correctiveInputPose').elements()
                
                for pose_input in pose_inputs:
                    if pose_input.isConnected():
                        pose_input.disconnect()
                        
                # Note: We can't actually delete array elements in Maya,
                # so we'll just disconnect everything and leave the element empty
                
                # Refresh the UI
                self.refresh_blendshapes_list()
                self.controlling_poses_list.clear()
                
            except Exception as e:
                pm.warning(f"Failed to delete corrective blendshape: {e}")