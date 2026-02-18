import inspect
from os.path import dirname
import sys
from PySide2 import QtWidgets
from shiboken2 import wrapInstance
import maya.OpenMayaUI as omui


def get_maya_main_win():
    main_win = omui.MQtUtil.mainWindow()
    return wrapInstance(int(main_win), QtWidgets.QWidget)


def reset_session_for_tool(user_path=None):
    if user_path is None:
        user_path = dirname(__file__)
    user_path = user_path.lower()

    modules_to_delete = []

    for key, module in sys.modules.items():
        try:
            module_file_path = inspect.getfile(module).lower()
            if module_file_path == __file__.lower():
                continue
            if module_file_path.startswith(user_path):
                modules_to_delete.append(key)
        except:
            pass
    
    for module in modules_to_delete:
        print("Removing module {}".format(module))
        del(sys.modules[module])


def hot_reload():
    reset_session_for_tool("D:\piper\_lib\maya\skylib")
    reset_session_for_tool()
