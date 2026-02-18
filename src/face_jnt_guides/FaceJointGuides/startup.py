import skylib.utils.module_utils as smu
from FaceJointGuides.ui.main_window import FaceJointGuides


def show_win():
    try:
        guides_ui.close()
        guides_ui.deleteLater()
    except:
        pass

    guides_ui = FaceJointGuides()
    guides_ui.show()


def start_tool():
    smu.reset_session_for_tool(r"D:\vitruvian\prj\face_rigger\src\face_jnt_guides\FaceJointGuides")
    smu.reset_session_for_tool()
    show_win()
