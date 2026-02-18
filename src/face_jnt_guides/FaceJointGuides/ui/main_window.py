import pymel.core as pm
from PySide2 import QtCore, QtWidgets
import skylib.utils.module_utils as smu
import FaceJointGuides.core.component_utils as cu
from FaceJointGuides.core.component import Component
from typing import Optional


class FaceJointGuides(QtWidgets.QDialog):
    def __init__(self, parent=smu.get_maya_main_win()):
        super(FaceJointGuides, self).__init__(parent)

        self.__set_cosmetics()
        self.__create_widgets()
        self.__create_layouts()
        self.__set_connections()
        self.__load_components()

    def __set_cosmetics(self):
        self.setWindowTitle("Face Joint Guides")
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowContextHelpButtonHint)
        self.setMinimumHeight(500)
        self.setMinimumWidth(300)

    def __create_widgets(self):
        self.build_rig_btn = QtWidgets.QPushButton('Build From Selection')

        self.components_list = QtWidgets.QListWidget()
        self.components_list.setFixedHeight(350)
        self.components_list.setFixedWidth(250)

        self.draw_component_btn = QtWidgets.QPushButton('Draw Component')
        self.init_hierarchy_btn = QtWidgets.QPushButton('Init Hierarchy')
        self.mirror_guides_btn = QtWidgets.QPushButton('Mirror Guides')

    def __create_layouts(self):
        main_layout = QtWidgets.QHBoxLayout(self)
        spacer_left = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        spacer_right = QtWidgets.QSpacerItem(0, 0, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)

        v_layout = QtWidgets.QVBoxLayout()
        v_layout.addWidget(self.build_rig_btn)
        v_layout.addWidget(self.components_list)
        v_layout.addWidget(self.draw_component_btn)
        v_layout.addWidget(self.init_hierarchy_btn)
        v_layout.addWidget(self.mirror_guides_btn)

        main_layout.addItem(spacer_left)
        main_layout.addLayout(v_layout)
        main_layout.addItem(spacer_right)

    def __set_connections(self):
        self.build_rig_btn.clicked.connect(self.__on_build_clicked)
        self.draw_component_btn.clicked.connect(self.__on_draw_component_clicked)
        self.init_hierarchy_btn.clicked.connect(self.__on_init_hierarchy_clicked)
        self.mirror_guides_btn.clicked.connect(self.__on_mirror_clicked)
        # Call draw when an item is double-clicked in the components list
        self.components_list.itemDoubleClicked.connect(lambda _: self.__on_draw_component_clicked())

    def __load_components(self):
        comps = cu.load_all_components()
        for component in comps:
            component_item = QtWidgets.QListWidgetItem(component.name)
            component_item.setData(QtCore.Qt.UserRole, component)
            self.components_list.addItem(component_item)

    def __on_draw_component_clicked(self):
        component = self.__get_selected_component()
        if component is None:
            return
        component.draw()

    @staticmethod
    def __on_build_clicked():
        cu.build_from_selection()

    @staticmethod
    def __on_init_hierarchy_clicked():
        cu.init_hierarchy()

    @staticmethod
    def __on_mirror_clicked():
        cu.mirror_guides()

    def __get_selected_component(self) -> Optional[Component]:
        selected_items = self.components_list.selectedItems()
        if len(selected_items) == 0:
            return None
        return selected_items[0].data(QtCore.Qt.UserRole)
