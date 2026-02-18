import FacePoseUI.ui.main_window
import skylib.utils.module_utils as smu


def start_tool():
    smu.reset_session_for_tool(r"D:\vitruvian\prj\face_rigger\src\face_pose_ui\FacePoseUI")
    smu.reset_session_for_tool()
    FacePoseUI.ui.main_window.show_win()
