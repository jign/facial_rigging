from FacePoseUI.core.side import Side
import pymel.core as pm
from FacePoseUI.core.driver_curve import DriverCurve
from FacePoseUI.core.subpose import Subpose
from typing import List, Optional
import FacePoseUI.core.naming.naming_tools as nt
import FacePoseUI.core.core_tools as ct
import skylib.utils.core_utils as sc


class Pose:
    def __init__(self):
        self.pose_attr: Optional[pm.Attribute] = None
        self.rig = None
        self.pose_idx = -1  # logical index on the driver

        self.subposes: List[Subpose] = []

    @staticmethod
    def new_pose(rig, host_obj: pm.PyNode, pose_name: str, min_val: float, max_val: float):
        """
        This doesn't connect the pose to any driven attributes yet, it just wires the pose control
        attribute to the first available input pose array element (poseWeight)
        This is because a Pose, by itself when created, doesn't have any subposes yet. It's just
        an empty container, which only needs to be wired to the driver's pose control plug.
        """    
        pose = Pose()
        pose.setup(host_obj, pose_name, min_val, max_val)
        pose.rig = rig
        pose.pose_idx = sc.find_next_available_index(f'{rig.driver}', 'poses')
        pose.connect_to_driver()   
        return pose     

    def setup(self, host_obj: pm.PyNode, name, min_val, max_val):
        host_obj.addAttr(name, nn=name, keyable=True, attributeType='double', min=min_val, max=max_val, hxv=True,
                         hnv=True)
        self.pose_attr = host_obj.attr(name)

    def get_name(self) -> str:
        return self.pose_attr.name(includeNode=False)

    def build_from_attr(self, attr: pm.Attribute, rig):
        """
        Builds a Pose object from a maya scene pose.
        This doesn't connect attributes, as they're already connected
        Attr is pm Attribute and str is ex. nurbsCircle1.l_out_brow_up
        """
        # 1. Set direct attributes
        self.pose_attr = attr
        self.rig = rig

        # 2. Wire derived attributes
        self.pose_idx = self.find_pose_index_in_driver()

        # 3. Wire subposes
        for curve in self.get_driver_curves():
            new_driver_curve = DriverCurve(curve, self.get_driver())
            new_sp = Subpose(new_driver_curve)
            self.subposes.append(new_sp)

    def delete(self):
        for i in reversed(range(0, len(self.subposes))):
            self.delete_subpose(self.subposes[i])
        self.pose_attr.disconnect()

    def connect_to_driver(self):
        driver_attr: pm.Attribute = self.get_driver().attr('poses')[self.pose_idx].attr('poseWeight')
        if not driver_attr.isConnected():
            self.pose_attr.connect(driver_attr)

    def capture_pose(self, obj_filter: Optional[List[pm.PyNode]] = None):
        should_filter = True if obj_filter is not None else False
        pose_weight = self.get_pose_weight()
        snapshot = {}

        for sp in self.subposes:
            if should_filter and sp.get_driven_object() not in obj_filter:
                continue
            driven_attr: pm.Attribute = sp.get_driven_attr()
            snapshot[driven_attr] = driven_attr.get()

        # This is done in two steps to make sure the driver isn't refreshing the plugs.
        for sp in self.subposes:
            if should_filter and sp.get_driven_object() not in obj_filter:
                continue
            sp.set_key(pose_weight, snapshot[sp.get_driven_attr()])

    def capture_key_for_subpose(self, subpose: Subpose):
        if subpose is not None:
            subpose.capture_key(self.get_pose_weight())
        else:
            print('Pose::capture_key_for_subpose error, no subpose being edited')

    def capture_obj(self, obj: pm.PyNode):
        pose_weight = self.get_pose_weight()
        for sp in self.get_subposes_for_obj(obj):
            sp.capture_key(pose_weight)

    def add_subpose(self, driven_attr: pm.Attribute) -> Subpose:
        new_subpose = Subpose.new_subpose(self.get_pose_name(), self.pose_attr, driven_attr, self.get_driver(),
                                          self.rig, self.pose_idx)
        if new_subpose not in self.subposes:
            self.subposes.append(new_subpose)
        return new_subpose

    def delete_subpose(self, subpose: Subpose):
        attr_to_clean_up = subpose.get_driven_attr()
        subpose.delete()
        self.subposes.remove(subpose)
        ct.clean_plug_from_driver(self.rig, attr_to_clean_up)

    def add_key(self, subpose: Subpose, pose_weight: float, attr_val: float):
        if subpose is None:
            return False

        res = subpose.add_key(pose_weight, attr_val)
        return res

    def remove_key(self, subpose: Subpose, key_idx: int):
        if subpose is None:
            return
        subpose.remove_key(key_idx)

    def get_driver_curves(self):
        # Begin with pose ex. nurbsCircle1.l_out_brow_up
        # all connections for the pose attribute
        conns = self.pose_attr.listConnections(p=1)
        curves = []
        for conn_attr in conns:
            # print(f'{conn_attr.plugNode().name()}')
            plug_name = conn_attr.plugNode().name()
            if 'acUU' in plug_name or 'acUA' in plug_name:
                curves.append(conn_attr.plugNode())
        return curves

    def find_pose_index_in_driver(self) -> Optional[int]:
        """
        Assumes all data has been set up except for the pose index
        """
        driver = self.get_driver()
        elems = driver.attr('poses').elements()
        filtered_elems = [elem for elem in elems if 'poseWeight' in elem]
        for pw in filtered_elems:
            if driver.attr(pw).isConnected():
                # poseWeight should have only one input
                pose_attr = driver.attr(pw).inputs(p=1)[0]
                if pose_attr == self.pose_attr:
                    # print(f'Pose index for pose {self.get_pose_name()} is {driver.attr(pw).parent().index()}')
                    return driver.attr(pw).parent().index()
        print(f"we have a pose without a weight {self.get_pose_name()}")
        return None

    def get_subposes_for_obj(self, obj) -> List[Subpose]:
        subposes = []
        for sp in self.subposes:
            if obj == sp.get_driven_object() and sp not in subposes:
                subposes.append(sp)
        return subposes

    def get_pose_weight(self) -> float:
        return self.pose_attr.get()

    def get_host_obj(self) -> pm.PyNode:
        return self.pose_attr.node()

    def get_host_obj_name(self) -> str:
        return self.get_host_obj().getName()

    def get_pose_name(self) -> str:
        return self.pose_attr.name(includeNode=False)

    def get_min_val(self) -> float:
        return self.pose_attr.getMin()

    def get_max_val(self) -> float:
        return self.pose_attr.getMax()

    def get_driver(self) -> pm.PyNode:
        """
        Returns the facePoseDriver node.
        """
        return self.rig.driver

    def get_pose_side(self) -> Side:
        node_name = self.get_host_obj().getName()
        return nt.get_side(node_name)

    def __str__(self) -> str:
        # TODO I think this isn't necessary, I think just {attr} itself is enough
        # return f'{self.pose_attr.nodeName()}.{self.get_pose_name()}'
        return self.pose_attr.name()
