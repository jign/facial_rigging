import pymel.core as pm
from PySide2 import QtCore, QtWidgets
import skylib.utils.module_utils as smu
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose
import FacePoseUI.ui.util.factory_util as fu
from FacePoseUI.ui_control.face_pose_presenter import FacePosePresenter
from typing import List
from pathlib import Path


class FacePoseUi(QtWidgets.QDialog):
    def __init__(self, parent=smu.get_maya_main_win()):
        super(FacePoseUi, self).__init__(parent)

        self.scene_change_callback = None  # Store callback ID for cleanup

        self.presenter = FacePosePresenter()
        self.presenter.set_view(self)

        self.__set_cosmetics()
        self.__create_widgets()
        self.__create_layouts()
        self.__create_conns()

        # Register scene changed callback
        self.__register_scene_callback()

    def closeEvent(self, event):
        """Clean up callbacks when UI is closed (overridden method)"""
        if self.scene_change_callback is not None:
            pm.scriptJob(kill=self.scene_change_callback, f=True)
        if self.undo_callback is not None:
            pm.scriptJob(kill=self.undo_callback, f=True)
        if self.redo_callback is not None:
            pm.scriptJob(kill=self.redo_callback, f=True)
        super(FacePoseUi, self).closeEvent(event)

    def set_driver(self):
        self.presenter.set_driver()

    def update_driver_display(self, driver_name):
        self.current_weight_driver_label.setText(driver_name)
        self.current_weight_driver_label.setStyleSheet('QLabel {background-color: #f553be; padding: 2}')

    def select_pose(self, pose):
        """Select the given pose in the UI"""
        for i in range(self.pose_list.count()):
            item = self.pose_list.item(i)
            if item.data(QtCore.Qt.UserRole) == pose:
                self.pose_list.setCurrentItem(item)
                break

    def select_subpose(self, subpose):
        """Select the given subpose in the UI"""
        for i in range(self.subposes_list.count()):
            item = self.subposes_list.item(i)
            if item.data(QtCore.Qt.UserRole) == subpose:
                self.subposes_list.setCurrentItem(item)
                break

    def refresh_attrs_in_driver(self, driven_dict):
        """
        Refreshes the attributes displayed in the driver tree while preserving the expanded state and selection.
        This method performs the following steps:
        1. Saves the current expanded state of tree items
        2. Saves the current selection state of both top-level and child items
        3. Clears the tree and rebuilds it with fresh data from the rig
        4. Restores the previously saved expansion state
        5. Restores the previously saved selection state
        The tree structure represents Maya objects and their attributes that are driven by the facial rig.
        Each top-level item corresponds to a Maya object, and its children represent the attributes of that object.
        Returns:
            None
        """
        # Save the expanded state and selection before clearing
        expanded_items = {}
        selected_items = []
        
        # Save expanded state
        root = self.attrs_in_driver_tree.invisibleRootItem()
        for i in range(root.childCount()):
            item = root.child(i)
            if item.isExpanded():
                expanded_items[item.text(0)] = True
            
            # Save selection state for top-level items
            if item.isSelected():
                selected_items.append((item.text(0), None))
                
            # Handle child items
            for j in range(item.childCount()):
                child = item.child(j)
                if child.isSelected():
                    selected_items.append((item.text(0), child.text(0)))
        
        # Now clear and rebuild the tree
        self.attrs_in_driver_tree.clear()

        driven_objs: List[pm.PyNode] = driven_dict.keys()
        for obj in driven_objs:
            item: QtWidgets.QTreeWidgetItem = fu.create_attrs_in_rig_tree_item(obj.getName())
            item.setData(0, QtCore.Qt.UserRole, obj)
            self.attrs_in_driver_tree.addTopLevelItem(item)
            
            # Restore expansion state for this item
            if obj.getName() in expanded_items:
                item.setExpanded(True)
                
            for attr in driven_dict[obj]:
                # attr is a pm.Attribute
                child_item = fu.create_attrs_in_rig_tree_item(attr.name(includeNode=False))
                child_item.setData(0, QtCore.Qt.UserRole, obj)
                child_item.setData(1, QtCore.Qt.UserRole, attr)
                item.addChild(child_item)
                
        # Restore selection
        for parent_text, child_text in selected_items:
            # Find matching items
            matching_parents = self.attrs_in_driver_tree.findItems(parent_text, QtCore.Qt.MatchExactly, 0)
            if matching_parents:
                parent_item = matching_parents[0]
                if child_text is None:
                    # Select the parent
                    parent_item.setSelected(True)
                else:
                    # Find and select the child
                    for i in range(parent_item.childCount()):
                        child = parent_item.child(i)
                        if child.text(0) == child_text:
                            child.setSelected(True)
                            break

    def refresh_pose_list(self, poses: List[Pose]):
        self.pose_list.clear()
        for p in poses:
            item_wgt = QtWidgets.QListWidgetItem()
            item_wgt.setData(QtCore.Qt.UserRole, p)
            item_wgt.setText(f'{p}')
            self.pose_list.addItem(item_wgt)

    def refresh_subpose_list(self, subposes: List[Subpose]):
        self.subposes_list.clear()
        for sp in subposes:
            sp_item = QtWidgets.QListWidgetItem(sp.get_name())
            sp_item.setData(QtCore.Qt.UserRole, sp)
            self.subposes_list.addItem(sp_item)

    def add_subposes_from_dialog(self):
        self.presenter.add_subposes_from_dialog()

    def add_attrs_to_driver(self):
        self.presenter.add_attrs_to_driver()

    def delete_current_subpose(self):
        self.presenter.delete_current_subpose()

    def capture_selected(self):
        self.presenter.capture_selected()

    def capture_pose(self):
        self.presenter.capture_pose()

    def capture_key(self):
        self.presenter.capture_key()

    def del_key(self):
        selected_spreadsheet_rows = self.keys_spreadsheet.selectedItems()
        if len(selected_spreadsheet_rows) < 1:
            print('no key selected')
            return

        selected_row = selected_spreadsheet_rows[0].row()
        key_item = self.keys_spreadsheet.item(selected_row, 0)
        key_idx = key_item.data(QtCore.Qt.UserRole)
        self.presenter.delete_key(key_idx)

    def new_pose(self):
        self.presenter.new_pose()

    def delete_selected_pose(self):
        self.presenter.delete_current_pose()

    def mirror_pose(self):
        self.presenter.mirror_current_pose()

    def on_pose_list_elem_clicked(self, item):
        """
        On pose clicked, refresh list of subposes
        """
        new_selected_pose: Pose = item.data(QtCore.Qt.UserRole)
        self.presenter.on_pose_selected(new_selected_pose)

    def clear_keys_spreadsheet(self):
        # Clear the keys spreadsheet
        self.keys_spreadsheet.setRowCount(0)

    def on_subpose_selected(self, item):
        current_subpose = item.data(QtCore.Qt.UserRole)
        self.presenter.on_subpose_selected(current_subpose)

    def refresh_keys_spreadsheet(self, subpose):
        """
        Updates the keys spreadsheet UI to display the data from the given subpose.
        
        Args:
            subpose: The Subpose object whose keys should be displayed
        """
        self.__set_keys_spreadsheet_cell_changed_conn_enabled(False)
        
        self.keys_spreadsheet.setRowCount(0)
        
        keys = subpose.get_num_keys()
        for i in range(keys):
            self.keys_spreadsheet.insertRow(i)

            keynum_item = QtWidgets.QTableWidgetItem(f'{i}')
            keynum_item.setData(QtCore.Qt.UserRole, i)
            keynum_item.setFlags(keynum_item.flags() ^ QtCore.Qt.ItemIsEnabled)
            self.keys_spreadsheet.setItem(i, 0, keynum_item)

            weight_item = QtWidgets.QTableWidgetItem(subpose.weight_to_str(i))
            weight_item.setData(QtCore.Qt.UserRole, subpose.get_key_weight(i))
            self.keys_spreadsheet.setItem(i, 1, weight_item)

            val_item = QtWidgets.QTableWidgetItem(subpose.val_to_str(i))
            val_item.setData(QtCore.Qt.UserRole, subpose.get_key_val(i))
            self.keys_spreadsheet.setItem(i, 2, val_item)

        self.__set_keys_spreadsheet_cell_changed_conn_enabled(True)

    def on_keys_spreadsheet_cell_changed(self, row, column):
        def revert(msg):
            """
            Reverts a cell back to its previous state due to some error.
            """
            print(msg)
            item.setText(f'{prev_val:.2f}')
            self.__set_keys_spreadsheet_cell_changed_conn_enabled(True)

        self.__set_keys_spreadsheet_cell_changed_conn_enabled(False)

        item = self.keys_spreadsheet.item(row, column)
        key_idx = self.keys_spreadsheet.item(row, 0).data(QtCore.Qt.UserRole)
        prev_val = item.data(QtCore.Qt.UserRole)

        try:
            new_val = float(item.text())
        except ValueError:
            revert('Entered a non float value, reverting back to previous value. No changes were made to the scene.')
            return

        if column == 1:
            res = self.presenter.try_update_key_weight(key_idx, new_val)
            if res is False:
                revert('Failed to update subpose. Possibly entered a bad key')
                return
            else:
                # Only update the cell data if we didn't revert
                item.setData(QtCore.Qt.UserRole, new_val)
        elif column == 2:
            res = self.presenter.try_update_key_value(key_idx, new_val)
            if res is False:
                revert('Failed to update subpose. Possibly entered a bad key')
                return
            else:
                # Only update the cell data if we didn't revert
                item.setData(QtCore.Qt.UserRole, new_val)

        self.__set_keys_spreadsheet_cell_changed_conn_enabled(True)

    def add_subposes_for_selected_attrs(self):
        if len(self.attrs_in_driver_tree.selectedItems()) == 0:
            return
        
        # Store the current Maya selection
        current_maya_selection = pm.selected()

        driven_attr_items = self.attrs_in_driver_tree.selectedItems()
        attrs_to_add = [attr_item.data(1, QtCore.Qt.UserRole) for attr_item in driven_attr_items]
        
        self.presenter.add_subposes(attrs_to_add)

        # Restore Maya selection
        if current_maya_selection:
            pm.select(current_maya_selection, replace=True)                

    def show_blendshapes_win(self):
        self.presenter.open_blendshapes_win()

    def serialize_rig(self):
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            "Save Rig",
            str(Path.home()),
            "JSON Files (*.json)"
        )        

        if file_path:
            out_path = Path(file_path)
            self.presenter.serialize_rig(out_path)   

    def deserialize_rig(self):
        # Use file dialog to get save location
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Save Rig",
            str(Path.home()),
            "JSON Files (*.json)"
        )        

        if file_path:
            read_path = Path(file_path)
            self.presenter.deserialize_rig(read_path)   

    def __set_cosmetics(self):
        self.setWindowTitle("Face Pose UI")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setMinimumHeight(300)
        self.setMinimumWidth(500)

    def __create_widgets(self):
        ###########################################################
        # CURRENT WEIGHT DRIVER WIDGETS
        ###########################################################
        self.current_weight_driver_label = QtWidgets.QLabel('no driver selected')
        self.current_weight_driver_label.setStyleSheet('QLabel {background-color: red; padding: 2}')
        self.current_weight_driver_label.setMinimumWidth(175)
        self.choose_driver_node_btn = QtWidgets.QPushButton("...")
        self.choose_driver_node_btn.setFixedWidth(30)

        ###########################################################
        # POSE EDITOR WIDGETS
        ###########################################################
        self.pose_list = QtWidgets.QListWidget()
        self.pose_list.setFixedHeight(250)
        self.pose_list.setFixedWidth(200)
        self.pose_list.setToolTip("List of poses in the current rig")

        self.new_pose_btn = QtWidgets.QPushButton('+')
        self.new_pose_btn.setToolTip("Create a new pose")
        self.del_pose_btn = QtWidgets.QPushButton('-')
        self.del_pose_btn.setToolTip("Delete the selected pose")
        self.mirror_sym_btn = QtWidgets.QPushButton('*(+/-)')
        self.mirror_sym_btn.setToolTip("Mirror the selected pose to the opposite side")
        # Set button size
        self.new_pose_btn.setFixedWidth(40)
        self.del_pose_btn.setFixedWidth(40)
        self.mirror_sym_btn.setFixedWidth(40)

        ###########################################################
        # SUBPOSES WIDGETS
        ###########################################################
        self.subposes_list = QtWidgets.QListWidget()
        self.subposes_list.setFixedHeight(250)
        self.subposes_list.setMinimumWidth(125)
        self.subposes_list.setToolTip("Subposes for the currently selected pose")

        self.capture_attrs_from_scene_btn = QtWidgets.QPushButton('Set Driven Objects')
        self.del_subpose_btn = QtWidgets.QPushButton('-')
        self.del_subpose_btn.setFixedWidth(40)
        self.del_subpose_btn.setToolTip("Delete the selected subpose")

        self.attrs_in_driver_tree = QtWidgets.QTreeWidget()
        self.attrs_in_driver_tree.setHeaderHidden(True)
        self.attrs_in_driver_tree.setMaximumHeight(250)

        self.filter_objs_in_driver_le = QtWidgets.QLineEdit()
        self.filter_objs_in_driver_le.setPlaceholderText('Filter objects...')

        self.add_driven_attr_to_pose_btn = QtWidgets.QPushButton('<<<')
        self.add_driven_attr_to_pose_btn.setStyleSheet('QPushButton {background-color: #f553be; color: black;}')
        self.add_driven_attr_to_pose_btn.setMaximumWidth(30)
        self.add_driven_attr_to_pose_btn.setToolTip("Add selected attributes from the right panel to the current pose")


        self.add_attr_to_driver_btn = QtWidgets.QPushButton('+')
        self.add_attr_to_driver_btn.setFixedWidth(40)
        self.add_attr_to_driver_btn.setToolTip("Add attributes from a selected Maya object to the rig driver")
        # TODO filter objs attrs by t,r,s

        ###########################################################
        # KEYS EDITOR WIDGETS
        ###########################################################
        self.keys_spreadsheet = QtWidgets.QTableWidget()
        self.keys_spreadsheet.setColumnCount(3)
        self.keys_spreadsheet.setColumnWidth(0, 22)
        self.keys_spreadsheet.setColumnWidth(1, 90)
        self.keys_spreadsheet.setColumnWidth(2, 90)
        self.keys_spreadsheet.setHorizontalHeaderLabels(['Key', 'Pose Weight', 'Attribute Value'])

        self.capture_selected_btn = QtWidgets.QPushButton('Capture Selected')
        self.capture_selected_btn.setToolTip("Captures the current pose from selected Maya objects only.\n"
                                    "Creates or updates all subpose keys only for those selected objects.")

        self.capture_pose_btn = QtWidgets.QPushButton('Capture Pose')
        self.capture_pose_btn.setToolTip("Captures pose values for all driven objects in this pose.\n"
                                    "Creates or updates all keys for all subposes in the current pose.")        

        self.capture_key_btn = QtWidgets.QPushButton('Capture Key')
        self.capture_key_btn.setToolTip("Captures a key only for the selected subpose at the current pose weight.\n"
                                   "Only affects the currently selected subpose in the list.")
        
        self.del_key_btn = QtWidgets.QPushButton('Delete Key')
        self.del_key_btn.setToolTip("Deletes the selected key from the spreadsheet.\n"
                               "Select a row in the spreadsheet first before clicking.")

    def __create_layouts(self):

        ###########################################################
        # DRIVER NODE SELECTION
        ###########################################################

        node_layout = QtWidgets.QHBoxLayout()
        node_layout.addStretch()
        node_layout.addWidget(self.current_weight_driver_label)
        node_layout.addWidget(self.choose_driver_node_btn)
        node_layout.addStretch()

        ###########################################################
        # POSE EDITOR
        ###########################################################

        pose_list_lay = QtWidgets.QVBoxLayout()
        pose_actions_btns_lay = QtWidgets.QHBoxLayout()
        pose_actions_btns_lay.addWidget(self.new_pose_btn)
        pose_actions_btns_lay.addWidget(self.del_pose_btn)
        pose_actions_btns_lay.addWidget(self.mirror_sym_btn)
        pose_list_lay.addWidget(self.pose_list)
        pose_list_lay.addLayout(pose_actions_btns_lay)

        attrs_in_pose_lay = QtWidgets.QVBoxLayout()
        attrs_in_pose_actions_btns_lay = QtWidgets.QHBoxLayout()
        attrs_in_pose_actions_btns_lay.addWidget(self.capture_attrs_from_scene_btn)
        attrs_in_pose_actions_btns_lay.addWidget(self.del_subpose_btn)
        attrs_in_pose_lay.addWidget(self.subposes_list)
        attrs_in_pose_lay.addLayout(attrs_in_pose_actions_btns_lay)

        rig_objs_layout = QtWidgets.QVBoxLayout()
        rig_objs_actions_btns_lay = QtWidgets.QHBoxLayout()
        rig_objs_actions_btns_lay.addWidget(self.add_attr_to_driver_btn)
        rig_objs_layout.addWidget(self.attrs_in_driver_tree)
        rig_objs_actions_btns_lay.addWidget(self.filter_objs_in_driver_le)
        rig_objs_layout.addLayout(rig_objs_actions_btns_lay)

        pose_layout = QtWidgets.QHBoxLayout()
        pose_layout.addLayout(pose_list_lay)
        pose_layout.addLayout(attrs_in_pose_lay)
        pose_layout.addWidget(self.add_driven_attr_to_pose_btn)
        pose_layout.addLayout(rig_objs_layout)

        keys_layout = QtWidgets.QHBoxLayout()
        pose_editor_lay = QtWidgets.QVBoxLayout()

        capture_pose_lay = QtWidgets.QHBoxLayout()
        capture_pose_lay.addWidget(self.capture_selected_btn)
        capture_pose_lay.addWidget(self.capture_pose_btn)

        keys_editor_lay = QtWidgets.QHBoxLayout()
        keys_editor_lay.addWidget(self.capture_key_btn)
        keys_editor_lay.addWidget(self.del_key_btn)

        pose_editor_lay.addLayout(capture_pose_lay)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        pose_editor_lay.addWidget(sep)

        pose_editor_lay.addLayout(keys_editor_lay)
        pose_editor_lay.addStretch()

        keys_layout.addLayout(pose_editor_lay)
        keys_layout.addWidget(self.keys_spreadsheet)

        main_editor_layout = QtWidgets.QVBoxLayout()
        main_editor_layout.addLayout(pose_layout)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_editor_layout.addWidget(sep)
        main_editor_layout.addLayout(keys_layout)

        tb = QtWidgets.QToolBar()

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(tb)
        main_layout.addLayout(node_layout)
        sep = QtWidgets.QFrame()
        sep.setFrameShape(QtWidgets.QFrame.HLine)
        sep.setFrameShadow(QtWidgets.QFrame.Sunken)
        main_layout.addWidget(sep)
        main_layout.addLayout(main_editor_layout)

        ###########################################################
        # TOOLBAR
        ###########################################################

        self.show_pose_pane_action = QtWidgets.QAction("pose", tb)
        self.show_key_attrs_action = QtWidgets.QAction("attr", tb)
        self.show_blendshapes_editor_action = QtWidgets.QAction("blendshapes", tb)
        self.save_rig_action = QtWidgets.QAction("save rig", tb)
        self.load_rig_action = QtWidgets.QAction('load rig', tb)
        self.show_keys_editor_action = QtWidgets.QAction('keys', tb)
        tb.addActions([
            self.show_pose_pane_action,
            self.show_key_attrs_action,
            self.show_keys_editor_action,
            self.show_blendshapes_editor_action,
            self.save_rig_action,
            self.load_rig_action]
        )

    def __create_conns(self):
        self.choose_driver_node_btn.clicked.connect(self.set_driver)

        self.new_pose_btn.clicked.connect(self.new_pose)
        self.del_pose_btn.clicked.connect(self.delete_selected_pose)
        self.mirror_sym_btn.clicked.connect(self.mirror_pose)

        self.add_driven_attr_to_pose_btn.clicked.connect(self.add_subposes_for_selected_attrs)
        self.add_attr_to_driver_btn.clicked.connect(self.add_attrs_to_driver)
        self.del_subpose_btn.clicked.connect(self.delete_current_subpose)

        self.capture_attrs_from_scene_btn.clicked.connect(self.add_subposes_from_dialog)

        self.capture_selected_btn.clicked.connect(self.capture_selected)
        self.capture_pose_btn.clicked.connect(self.capture_pose)
        self.capture_key_btn.clicked.connect(self.capture_key)
        self.del_key_btn.clicked.connect(self.del_key)

        self.pose_list.itemClicked.connect(self.on_pose_list_elem_clicked)
        self.subposes_list.itemClicked.connect(self.on_subpose_selected)

        self.__set_keys_spreadsheet_cell_changed_conn_enabled(True)

        self.show_blendshapes_editor_action.triggered.connect(self.show_blendshapes_win)
        self.save_rig_action.triggered.connect(self.serialize_rig)
        self.load_rig_action.triggered.connect(self.deserialize_rig)

    def __set_keys_spreadsheet_cell_changed_conn_enabled(self, enabled):
        """
        I don't remember exactly why this is here, but I vaguely recall it was to fix an annoying bug. The answer is most likely in one of Chris Zurbrigg's tutorials. Pretty sure I got it from there.
        """
        if enabled:
            self.keys_spreadsheet.cellChanged.connect(self.on_keys_spreadsheet_cell_changed)
        else:
            self.keys_spreadsheet.cellChanged.disconnect(self.on_keys_spreadsheet_cell_changed)

    def __register_scene_callback(self):
        """Register a callback to refresh UI when the Maya scene changes"""
        self.scene_change_callback = pm.scriptJob(
            event=["SceneOpened", self.__on_scene_changed],
            protected=True
        )
        
        # Additional callbacks for other scene change events
        self.undo_callback = pm.scriptJob(
            event=["Undo", self.__on_scene_changed],
            protected=True
        )
        self.redo_callback = pm.scriptJob(
            event=["Redo", self.__on_scene_changed],
            protected=True
        )

    def __on_scene_changed(self):
        """Called when scene changes to refresh the UI"""
        self.presenter.on_scene_changed()


def show_win():
    try:
        face_pose_ui.close()
        face_pose_ui.deleteLater()
    except:
        pass

    face_pose_ui = FacePoseUi()
    face_pose_ui.show()
