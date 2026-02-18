from typing import List, Union
import pymel.core as pm
from FacePoseUI.core.rig import Rig
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose


def capture_selected_objects(pose: Pose):
    """Capture the selected objects to the rig"""
    objects = pm.selected()
    pose.capture_pose(objects)


def capture_pose(pose: Pose):
    pose.capture_pose()


def capture_key_for_subpose(pose: Pose, subpose: Subpose):
    pose.capture_key_for_subpose(subpose)


def try_update_key_value(subpose: Subpose, key_idx, new_val) -> bool:
    if key_idx != -1:
        return subpose.try_change_key_value(key_idx, new_val)
    return False


def try_update_key_weight(subpose: Subpose, key_idx, new_val) -> bool:
    if key_idx != -1:
        return subpose.try_change_key_weight(key_idx, new_val)
    return False


def del_key_for_subpose(pose: Pose, subpose: Subpose, key_idx: int) -> bool:
    if key_idx != -1:
        pose.remove_key(subpose, key_idx)
        return True
    return False