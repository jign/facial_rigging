import pymel.core as pm
from PySide2 import QtCore, QtWidgets
import skylib.utils.module_utils as smu
from typing import List, Optional
import os


class DriverNameDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(DriverNameDialog, self).__init__(parent)
        self.setWindowTitle('New Face Driver')

        # Create widgets
        self.name_label = QtWidgets.QLabel("Driver Name:")
        self.name_input = QtWidgets.QLineEdit()
        self.name_input.setText("faceDriver")
        self.name_input.selectAll()

        # Create buttons
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        # Create layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.name_label)
        layout.addWidget(self.name_input)
        layout.addWidget(self.buttons)

        # Set size
        self.setMinimumWidth(300)

    def get_name(self):
        return self.name_input.text()

    @staticmethod
    def get_driver_name(parent=None):
        dialog = DriverNameDialog(parent)
        result = dialog.exec_()

        if result == QtWidgets.QDialog.Accepted:
            return dialog.get_name()
        return None


class SelectDriverDialog(QtWidgets.QDialog):
    def __init__(self, parent=smu.get_maya_main_win()):
        super(SelectDriverDialog, self).__init__(parent)

        self.setWindowTitle('Select Face Driver')

        self.create_wigets()
        self.create_layouts()
        self.create_conns()

        self.refresh_list()

    def create_wigets(self):
        self.drivers_list = QtWidgets.QListWidget()
        self.accept_btn = QtWidgets.QPushButton('accept')
        self.accept_btn.setEnabled(False)  # Initially disabled
        self.create_btn = QtWidgets.QPushButton('New Driver')
        self.plugin_warning = QtWidgets.QLabel("")
        self.plugin_warning.setStyleSheet("color: red;")
        self.plugin_warning.setVisible(False)

    def create_layouts(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addWidget(self.plugin_warning)
        main_layout.addWidget(self.drivers_list)

        buttons_layout = QtWidgets.QHBoxLayout()
        buttons_layout.addWidget(self.create_btn)
        buttons_layout.addWidget(self.accept_btn)

        main_layout.addLayout(buttons_layout)

    def create_conns(self):
        self.accept_btn.clicked.connect(self.select_current)
        self.create_btn.clicked.connect(self.create_new_driver)
        self.drivers_list.itemSelectionChanged.connect(self.update_accept_button)
        self.drivers_list.itemDoubleClicked.connect(self.accept)  # Add double click functionality

    def update_accept_button(self):
        self.accept_btn.setEnabled(len(self.drivers_list.selectedItems()) > 0)

    def is_faceposedriver_available(self):
        # Check if the node type exists by querying Maya about the node type
        try:
            return pm.nodeType('facePoseDriver', isTypeName=True)
        except:
            return False

    def refresh_list(self):
        self.drivers_list.clear()

        if not self.is_faceposedriver_available():
            self.plugin_warning.setText("FacePoseDriver plugin not loaded. Please load the FacePoseDriver.mll plugin.")
            self.plugin_warning.setVisible(True)
            # Keep create button enabled
            return

        self.plugin_warning.setVisible(False)

        drivers: List[pm.PyNode] = pm.ls(typ='facePoseDriver')
        for d in drivers:
            wdgt = QtWidgets.QListWidgetItem(d.getName())
            wdgt.setData(QtCore.Qt.UserRole, d)
            self.drivers_list.addItem(wdgt)

        # Update accept button after refresh
        self.update_accept_button()

    def create_new_driver(self):
        """Handles the creation of a new facePoseDriver node, including plugin loading if necessary."""
        if not self.is_faceposedriver_available():
            result = QtWidgets.QMessageBox.question(
                self,
                "Plugin Required",
                "The FacePoseDriver plugin is not loaded. Do you want to try loading it now?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )

            if result == QtWidgets.QMessageBox.Yes:
                hardcoded_path = r"D:/vitruvian/prj/face_rigger/src/face_pose_driver/FacePoseDriver/Release/Debug"
                start_dir = hardcoded_path if os.path.isdir(hardcoded_path) else os.getcwd()
                plugin_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                    self,
                    "Select FacePoseDriver Plugin",
                    start_dir,
                    "Plugin Files (*.mll *.so *.dll);;All Files (*)"
                )
                if not plugin_path:
                    return  # User cancelled the file dialog

                try:
                    pm.loadPlugin(plugin_path)
                    # Refresh the list after loading the plugin
                    self.refresh_list()
                except Exception as e:
                    QtWidgets.QMessageBox.critical(
                        self,
                        "Error Loading Plugin",
                        f"Could not load the FacePoseDriver plugin: {str(e)}"
                    )
            return

        # Prompt for name
        driver_name = DriverNameDialog.get_driver_name(self)
        if not driver_name:
            return  # User canceled the name dialog

        # Create a new facePoseDriver node
        try:
            new_node = pm.createNode('facePoseDriver', name=driver_name)
            # Refresh the list to show the new node
            self.refresh_list()

            # Select the newly created node in the list
            for i in range(self.drivers_list.count()):
                item = self.drivers_list.item(i)
                if item.data(QtCore.Qt.UserRole) == new_node:
                    self.drivers_list.setCurrentItem(item)
                    break
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Error Creating Node",
                f"Failed to create facePoseDriver node: {str(e)}"
            )

    def select_current(self):
        if not len(self.drivers_list.selectedItems()) > 0:
            return

        self.accept()

    def get_selected_driver(self) -> Optional[pm.PyNode]:
        try:
            if len(self.drivers_list.selectedItems()) > 0:
                return self.drivers_list.selectedItems()[0].data(QtCore.Qt.UserRole)
            return None
        except Exception:
            return None

    @staticmethod
    def get_driver(parent=smu.get_maya_main_win()):
        dialog = SelectDriverDialog(parent=parent)
        dialog.exec_()
        return dialog.get_selected_driver()
