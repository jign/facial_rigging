import pymel.core as pm
from PySide2 import QtCore, QtWidgets, QtGui
import maya.api.OpenMaya as om
import skylib.utils.module_utils as smu
from typing import List, Callable


class SetDrivenObjsDialog(QtWidgets.QDialog):
    def __init__(self, callback: Callable[[List[pm.Attribute]], None], parent=smu.get_maya_main_win()):
        super(SetDrivenObjsDialog, self).__init__(parent)

        self.callback = callback
        self.setWindowTitle('Set Driven Objects')
        self.resize(375, 250)
        
        # Allow interaction with Maya while dialog is open
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.Window)

        self.create_widgets()
        self.create_layouts()
        self.create_conns()

    def create_widgets(self):
        self.driven_obj_list = QtWidgets.QListWidget()
        self.driven_obj_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.driven_attrs_list = QtWidgets.QListWidget()
        self.driven_attrs_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        # Harcoding this as a feature
        # TODO I may want to set these dynamically based on the selected objects, but it's not something that matters right now
        # TODO for now, I'm only using translation. Rotation should work when implementing angular attributes, and scale when (if) fixing the driver
        # hardcoded_attrs = ['translate', 'rotate', 'scale']
        hardcoded_attrs = ['translate', 'rotate']
        hardcoded_axes = ['X', 'Y', 'Z']
        expanded_attrs = [a + b for a in hardcoded_attrs for b in hardcoded_axes]
        for attr in expanded_attrs:
            list_item = QtWidgets.QListWidgetItem(attr)
            self.driven_attrs_list.addItem(list_item)

        self.load_driven_btn = QtWidgets.QPushButton('Load Driven')
        self.add_to_pose_btn = QtWidgets.QPushButton('Add Selected To Pose')
        self.cancel_btn = QtWidgets.QPushButton('Cancel')

    def create_layouts(self):
        attrs_lay = QtWidgets.QHBoxLayout()
        attrs_lay.addWidget(self.driven_obj_list)
        attrs_lay.addWidget(self.driven_attrs_list)

        btns_lay = QtWidgets.QHBoxLayout()
        btns_lay.addWidget(self.load_driven_btn)
        btns_lay.addWidget(self.add_to_pose_btn)
        btns_lay.addWidget(self.cancel_btn)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(attrs_lay)
        main_layout.addLayout(btns_lay)

    def create_conns(self):
        self.load_driven_btn.clicked.connect(self.load_driven)
        self.add_to_pose_btn.clicked.connect(self.add_to_pose)
        self.cancel_btn.clicked.connect(self.cancel)

    def load_driven(self):
        self.driven_obj_list.clear()

        sel = pm.ls(sl=1)
        for s in sel:
            self.add_obj_item(s)

    def add_to_pose(self):
        attrs = self.get_selected_attrs()
        self.callback(attrs)
        self.close()

    def cancel(self):
        self.close()

    def closeEvent(self, event):
        # Handle the dialog being closed with the X button
        event.accept()

    def get_selected_attrs(self) -> List[pm.Attribute]:
        combined_attrs: List[pm.Attribute] = []

        for obj_item in self.driven_obj_list.selectedItems():
            obj_node: pm.PyNode = obj_item.data(QtCore.Qt.UserRole)
            for attr_item in self.driven_attrs_list.selectedItems():
                attr_str = attr_item.text()
                attr = obj_node.attr(attr_str)
                combined_attrs.append(attr)

        return combined_attrs

    def add_obj_item(self, item_name):
        obj_node = pm.PyNode(item_name)
        widget_item = QtWidgets.QListWidgetItem(obj_node.getName())
        widget_item.setData(QtCore.Qt.UserRole, obj_node)
        self.driven_obj_list.addItem(widget_item)

    @staticmethod
    def get_attrs(parent=smu.get_maya_main_win()) -> Callable[[Callable[[List[pm.Attribute]], None]], None]:
        """
        Creates a dialog that allows the user to select driven objects and attributes.
        
        Returns:
            A function that takes a callback. The callback will receive the selected attributes
            when the user confirms their selection.
        """
        def create_dialog_with_callback(callback):
            dialog = SetDrivenObjsDialog(callback, parent=parent)
            dialog.show()  # Non-modal
            return dialog
            
        return create_dialog_with_callback
