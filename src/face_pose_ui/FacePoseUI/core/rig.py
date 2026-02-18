from FacePoseUI.core.pose import Pose
from FacePoseUI.core.subpose import Subpose
import pymel.core as pm
import maya.api.OpenMaya as om
from typing import List, Set, Union, Optional
import FacePoseUI.core.core_tools as ct


# TODO try evaluateNumElements() to build the array block instead of my hacks
# TODO Maybe the Rig should keep a list of connected attributes to make it easier to filter without having to do if self.get_driven_attribute_index(attr) is not None:

class Rig:
    def __init__(self, driver: Optional[pm.PyNode]):
        # Can be None if we're rebuilding a rig from a file and we haven't created the driver node yet
        self.driver: pm.PyNode = driver

        self.poses: List[Pose] = []

        if self.driver:
            ct.force_refresh_driver_conns(self.driver)
            self.init_raw_poses()

    def set_driver(self, driver: pm.PyNode):
        # We don't refresh conns or init any poses because setting the driver means we're rebuilding the rig from scratch, so nothing to refresh.
        self.driver = driver

    def init_raw_poses(self):
        raw_poses = self.find_raw_poses()
        for raw_pose in raw_poses:
            pose = Pose()
            pose.build_from_attr(raw_pose, self)
            if pose not in self.poses:
                self.poses.append(pose)

    def add_pose(self, pose):
        if pose not in self.poses:
            self.poses.append(pose)

        ct.force_refresh_driver_conns(self.driver)

    def delete_pose(self, pose: Pose):
        self.poses.remove(pose)
        pose.delete()

    def delete_subpose(self, pose: Pose, subpose: Subpose):
        pose.delete_subpose(subpose)

    def add_subposes_to_pose(self, pose: Pose, attrs: Union[List[pm.Attribute], pm.Attribute]) -> List[Subpose]:
        if pose is None:
            om.MGlobal.displayWarning("FacePoseUI // Rig::add_subposes called with no pose selected.")
            return []
        if type(attrs) is not list:
            attrs = [attrs]
        new_subposes = []
        self.add_attrs_to_rig(attrs)
        for attr in attrs:
            new_subpose = pose.add_subpose(attr)
            new_subposes.append(new_subpose)
        return new_subposes

    def add_attrs_to_rig(self, attrs: List[pm.Attribute]):
        """
        This adds the attributes to the rig if they aren't already there.
        """
        if self.driver is None:
            om.MGlobal.displayWarning('FacePoseUI // Rig::add_attrs_to_rig Trying to add objects to the rig without a '
                                      'driver selected')
            return

        # We need to force a refresh due to the plug bug, possibly already fixed with setDependentsDirty implementation in the plugin
        ct.force_refresh_driver_conns(self.driver)

        # First make sure to filter each kind of attribute
        linear_attrs = [attr for attr in attrs if 'rotate' not in attr.name()]
        angular_attrs = [attr for attr in attrs if 'rotate' in attr.name()]
        for attr in linear_attrs:
            # Check if the attribute is already in the rig
            if ct.get_driven_linear_attribute_index(self.driver, attr) is not None:
                continue

            array_idx = ct.find_next_available_linear_index(self.driver)
            source_attr = self.driver.attr('linearOutputs')[array_idx]
            # I feel like this is unnecessary since get_driven_linear_attribute_index should take care of it
            # if source_attr.isConnected():
            #     om.MGlobal.displayError('FacePoseUI // Rig::add_attrs_to_rig trying to connect to a previously '
            #                             'connected attribute')
            source_attr.connect(attr, lock=False)

            # Important to handle the ugly plug bug, possibly already fixed with setDependentsDirty implementation in the plugin
            source_attr.get()

        for attr in angular_attrs:
            # Check if the attribute is already in the rig
            if ct.get_driven_angular_attribute_index(self.driver, attr) is not None:
                continue

            array_idx = ct.find_next_available_angular_index(self.driver)
            source_attr = self.driver.attr('angularOutputs')[array_idx]
            # if source_attr.isConnected():
            #     om.MGlobal.displayError('FacePoseUI // Rig::add_attrs_to_rig trying to connect to a previously '
            #                             'connected attribute')
            source_attr.connect(attr, lock=False)

            # Important to handle the ugly plug bug, possibly already fixed with setDependentsDirty implementation in the plugin
            source_attr.get()

    def is_rig_driving_attr(self, attr: pm.Attribute) -> bool:
        for pose in self.poses:
            for subpose in pose.subposes:
                if subpose.get_driven_attr() is attr:
                    return True
        return False      

    def get_poses(self) -> List[Pose]:
        return self.poses

    def get_control_objects(self) -> List[pm.PyNode]:
        objs: Set[pm.PyNode] = set()
        for pose in self.poses:
            objs.add(pose.get_host_obj())
        return list(objs)

    def add_key(self, pose: Pose, subpose: Subpose, time, val):
        if pose is None:
            return False
        res = pose.add_key(subpose, time, val)
        return res

    def find_raw_poses(self) -> List[pm.Attribute]:
        """
        Raw poses are attributes. The Pose() object needs to be built from them
        """
        elems = self.driver.attr('poses').elements()
        filtered_elems = [elem for elem in elems if 'poseWeight' in elem]
        out_poses: List[pm.Attribute] = []
        for pw in filtered_elems:
            if self.driver.attr(pw).isConnected():
                out_poses.append(self.driver.attr(pw).inputs(p=1)[0])
        return out_poses
