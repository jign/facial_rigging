import pymel.core as pm
from PySide2 import QtCore, QtWidgets
import skylib.utils.module_utils as smu


class AddAttrsToDriverDialog(QtWidgets.QDialog):
    def __init__(self, selected_obj=None, parent=smu.get_maya_main_win()):
        super(AddAttrsToDriverDialog, self).__init__(parent)

        self.parent = parent

        self.setWindowTitle('Add Attributes to Rig')

        self.selected_obj = selected_obj
        # Store attribute objects for easier retrieval
        self.attr_objects = {}

        self.create_widgets()
        self.create_layouts()
        self.create_conns()

        self.refresh()

    def create_widgets(self):
        self.attrs_list = QtWidgets.QListWidget()
        self.attrs_list.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.add_selected_attrs_btn = QtWidgets.QPushButton('Add Selected Attributes')

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.attrs_list)
        main_layout.addWidget(self.add_selected_attrs_btn)

    def create_conns(self):
        self.add_selected_attrs_btn.clicked.connect(self.add_selected_attrs)
        
    def refresh(self):
        if self.selected_obj:
            all_attrs = self.selected_obj.listAttr()
            keyable_attrs = [attr for attr in all_attrs if attr.isKeyable() and "visibility" not in f'{attr}']
            
            for attr in keyable_attrs:
                attr_name = f'{attr}'
                item = QtWidgets.QListWidgetItem(attr_name)
                self.attrs_list.addItem(item)
                # Store the actual attribute object with the display name as key
                self.attr_objects[attr_name] = attr

    def add_selected_attrs(self):
        self.accept()

    def get_selected_attrs(self):
        # Return the actual attribute objects instead of just names
        selected_items = self.attrs_list.selectedItems()
        selected_attrs = []
        
        for item in selected_items:
            attr_name = item.text()
            if attr_name in self.attr_objects:
                selected_attrs.append(self.attr_objects[attr_name])
        
        return selected_attrs

    @staticmethod
    def get_attrs(selected_obj, parent=smu.get_maya_main_win()):
        dialog = AddAttrsToDriverDialog(selected_obj, parent=parent)
        dialog.exec_()
        return dialog.get_selected_attrs()
