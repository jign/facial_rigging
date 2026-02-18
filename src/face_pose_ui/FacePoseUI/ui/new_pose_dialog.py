import pymel.core as pm
from PySide2 import QtCore, QtWidgets, QtGui
import maya.api.OpenMaya as om
import skylib.utils.module_utils as smu
from FacePoseUI.core.pose import Pose
import FacePoseUI.ui_control.pose_context as posec

class NewPoseDialog(QtWidgets.QDialog):
    def __init__(self, parent=smu.get_maya_main_win(), rig = None):
        super(NewPoseDialog, self).__init__(parent)

        self.parent = parent
        self.setWindowTitle("Add New Pose")

        self.listener_idx = None
        self.selected_obj : pm.PyNode = None
        self.rig = rig

        self.create_widgets()
        self.create_layouts()
        self.create_conns()

        self.register_selection_listener()

        self.refresh_obj()

    def closeEvent(self, event):
        if self.listener_idx is not None:
            om.MMessage.removeCallback(self.listener_idx)
        return super().closeEvent(event)

    def create_widgets(self):
        self.selected_obj_name_lbl = QtWidgets.QLabel('')
        self.attributes_list = QtWidgets.QListWidget()
        self.name_le = QtWidgets.QLineEdit()
        self.name_le.setPlaceholderText('pose name...')
        self.add_pose_btn = QtWidgets.QPushButton('Add Pose')
        self.min_val_label = QtWidgets.QLabel('Min')
        self.max_val_label = QtWidgets.QLabel('Max')
        validator = QtGui.QDoubleValidator()
        validator.setRange(-100, 100, decimals=2)
        self.min_val = QtWidgets.QLineEdit()
        self.min_val.setValidator(validator)
        self.min_val.setText('-10')
        self.max_val = QtWidgets.QLineEdit()
        self.max_val.setValidator(validator)
        self.max_val.setText('10')

    def create_layouts(self):
        pose_name_lay = QtWidgets.QHBoxLayout()
        pose_name_lay.addWidget(self.name_le)

        pose_vals_lay = QtWidgets.QHBoxLayout()
        pose_vals_lay.addWidget(self.min_val_label)
        pose_vals_lay.addWidget(self.min_val)
        pose_vals_lay.addWidget(self.max_val_label)
        pose_vals_lay.addWidget(self.max_val)

        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.selected_obj_name_lbl)
        main_layout.addWidget(self.attributes_list)
        main_layout.addLayout(pose_name_lay)
        main_layout.addLayout(pose_vals_lay)
        main_layout.addWidget(self.add_pose_btn)

    def create_conns(self):
        self.add_pose_btn.clicked.connect(self.add_pose)

    def register_selection_listener(self):
        self.listener_idx = om.MEventMessage.addEventCallback("SelectionChanged", self.refresh_obj)

    def refresh_obj(self, *args, **kwargs):
        self.attributes_list.clear()
        selection = pm.ls(sl=True)

        if len(selection) == 0:
            self.selected_obj_name_lbl.setText("no object selected")
            self.add_pose_btn.setEnabled(False)
            return
        
        self.add_pose_btn.setEnabled(True)
        self.selected_obj_name_lbl.setText(f'{selection[0]}')
        for attr in selection[0].listAttr(k=True):
            wdgt = QtWidgets.QListWidgetItem(attr.attrName(longName=True))
            wdgt.setData(QtCore.Qt.UserRole, attr)
            self.attributes_list.addItem(wdgt)

        self.selected_obj = pm.PyNode(selection[0])

    def add_pose(self):
        if not self.validate_pose():
            return

        pose_name = self.name_le.text()
        min_val = float(self.min_val.text())
        max_val = float(self.max_val.text())

        posec.new_pose(self.rig, self.selected_obj, pose_name, min_val, max_val)

        self.close()

    def get_selected_attr(self):
        return self.attributes_list.selectedItems()[0].data(QtCore.Qt.UserRole)

    def validate_pose(self):
        if self.rig.driver is None:
            return False
        return True