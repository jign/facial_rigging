from typing import List, Union
import pymel.core as pm
from FacePoseUI.core.rig import Rig
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose


def add_subposes_to_pose(rig: Rig, pose: Pose, attrs_for_subposes: List[pm.Attribute]):
    """Add subposes for the given attributes"""
    rig.add_subposes_to_pose(pose, attrs_for_subposes)


def add_attrs_to_rig(rig: Rig, attrs: List[pm.Attribute]):
    """Add attributes to the rig"""
    rig.add_attrs_to_rig(attrs)


def new_pose(rig: Rig, object: pm.PyNode, pose_name: str, min_val: float, max_val: float) -> Pose:
    """Add a new pose to the rig"""
    pose = Pose.new_pose(rig, object, pose_name, min_val, max_val)
    rig.add_pose(pose)
    return pose


def del_poses(rig: Rig, poses: Union[List[Pose], Pose]):
    """Delete the given subposes from the rig"""
    if type(poses) is not list:
        poses = [poses]
    for pose in poses:
        host_obj: pm.PyNode = pose.get_host_obj()
        pose_attr: pm.Attribute = pose.pose_attr
        rig.delete_pose(pose)
        # Delete the pose attribute after it's been removed from the rig
        if pm.attributeQuery(pose_attr.attrName(), node=host_obj, exists=True):
            pm.deleteAttr(pose_attr)


def del_subposes(rig: Rig, pose: Pose, subposes: Union[List[Subpose], Subpose]):
    """Delete the given subposes from the rig"""
    if type(subposes) is not list:
        subposes = [subposes]
    for subpose in subposes:
        rig.delete_subpose(pose, subpose)
