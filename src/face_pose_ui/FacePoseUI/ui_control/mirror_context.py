from typing import Optional
import pymel.core as pm
from FacePoseUI.core.rig import Rig
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose
from FacePoseUI.core.driver_curve import DriverCurve
import FacePoseUI.core.naming.naming_tools as nt


def find_mirror_pose(rig: Rig, pose: Pose) -> Optional[Pose]:
    """
    Attempts to find a corresponding pose in a mirrored host object.
    For example, l_brows_ctrl.brows_up_down will attempt to find
    the pose r_brows_ctrl.brows_up_down
    """
    pose_name = pose.get_pose_name()
    mirror_host_name = nt.get_mirrored_name(pose.get_host_obj_name())
    for p in rig.poses:
        if p.get_host_obj_name() == mirror_host_name:
            if p.get_pose_name() == pose_name:
                return p

    return None


def get_mirrored_driver_curve_name(driver_curve: DriverCurve) -> str:
    mirrored_driven_obj_name = nt.get_mirrored_name(driver_curve.get_driven_obj_name())
    return f'{mirrored_driven_obj_name}.{driver_curve.get_driven_attr_name()}'


def get_mirrored_subpose_name(subpose: Subpose) -> str:
    return get_mirrored_driver_curve_name(subpose.driver_curve)


def has_mirrored_equivalent(pose: Pose, mirrored_subpose) -> bool:
    mirrored_subpose_name = mirrored_subpose.get_name()
    for sp in pose.subposes:
        if get_mirrored_subpose_name(sp) is mirrored_subpose_name:
            return True
    return False


def mirror_subpose_keys_from_master(subpose: Subpose, master_subpose: Subpose):
    for i in range(0, master_subpose.get_num_keys()):
        master_weight = master_subpose.get_key_weight(i)
        master_val = master_subpose.get_key_val(i)
        # We're hardcoding the forward axis and only mirroring trans and rot
        # This could change in the future, but since it's an internal tool and we always use Z-forward axis and Y-up axis, it's safe to hardcode this
        should_negate = False
        if 'translateX' in f'{subpose.get_driven_attr()}':
            should_negate = True
        if 'rotateY' in f'{subpose.get_driven_attr()}':
            should_negate = True
        if 'rotateZ' in f'{subpose.get_driven_attr()}':
            should_negate = True
        mirrored_val = master_val if not should_negate else -master_val
        subpose.set_key(master_weight, mirrored_val)    


def update_mirrored_pose(mirrored_pose: Pose, master_pose: Pose):
    # 0. Delete non-existing poses
    for i in reversed(range(0, len(mirrored_pose.subposes))):
        sp = mirrored_pose.subposes[i]
        if not has_mirrored_equivalent(master_pose, sp):
            mirrored_pose.delete_subpose(mirrored_pose.subposes[i])

    # Create a copy of master subposes to track what needs to be created
    subposes_to_mirror = master_pose.subposes.copy()
    processed_indices = set()

    # 1. Update existing subposes
    for sp in mirrored_pose.subposes:
        for i, sp_to_mirror in enumerate(subposes_to_mirror):
            if sp.get_name() == get_mirrored_subpose_name(sp_to_mirror):
                sp.driver_curve.nuke_keys()
                mirror_subpose_keys_from_master(sp, sp_to_mirror)
                processed_indices.add(i)
                break

    # 2. Create the missing ones (those not in processed_indices)
    for i, subpose in enumerate(subposes_to_mirror):
        if i not in processed_indices:
            create_mirrored_subpose(mirrored_pose, subpose)


def create_mirrored_subpose(pose: Pose, subpose_to_mirror: Subpose) -> Subpose:
        mirrored_driven_obj_name = nt.get_mirrored_name(subpose_to_mirror.get_driven_obj_name())
        mirrored_driven_obj = pm.PyNode(mirrored_driven_obj_name)
        mirrored_attr = mirrored_driven_obj.attr(subpose_to_mirror.get_driven_attr().name(includeNode=False))

        pose.rig.add_attrs_to_rig([mirrored_attr])
        new_subpose = pose.add_subpose(mirrored_attr)
        mirror_subpose_keys_from_master(new_subpose, subpose_to_mirror)
        return new_subpose


def create_mirrored_pose(pose: Pose):
    # 1. Find corresponding host object
    mirror_host_name = nt.get_mirrored_name(pose.get_host_obj_name())
    mirror_host_obj = pm.PyNode(mirror_host_name)

    # 2. Create new pose
    # Remember that poses themselves don't have side information, the side depends on the host object, so both pose names will be the same. This is so that the animator can select both controls and see the same pose name, since maya will "merge" both attributes if they have the same name into one slider. Then the animator can, for example, select the controls for both brows, and some pose like "brows_up_down" will be applied to both brows.
    mirrored_pose = Pose.new_pose(pose.rig, mirror_host_obj, pose.get_pose_name(), pose.get_min_val(), pose.get_max_val())
    pose.rig.add_pose(mirrored_pose)
    # 3. Mirror subposes
    for subpose in pose.subposes:
        create_mirrored_subpose(mirrored_pose, subpose)


def mirror_pose(rig: Rig, pose: Pose):
    print("mirroring pose: ", pose.get_name())
    mirrored_pose = find_mirror_pose(rig, pose)
    if mirrored_pose is not None:
        print("found mirrored pose: ", mirrored_pose.get_name())
        update_mirrored_pose(mirrored_pose, pose)
    else:
        print("no mirrored pose found, creating one")
        create_mirrored_pose(pose)


def mirror_rig(rig: Rig):
    for pose in rig.poses:
        mirror_pose(rig, pose)
