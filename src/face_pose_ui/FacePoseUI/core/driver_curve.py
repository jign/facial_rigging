import pymel.core as pm
import pymel.util as pu
import FacePoseUI.core.naming.naming_tools as nt
import FacePoseUI.core.core_tools as ct
from typing import Optional


class DriverCurve:
    """
    Wrapper for angular and linear anim curves.
    The UI treats them as the same thing and this class handles the internals.
    """
    def __init__(self, curve: pm.PyNode, in_driver: pm.PyNode = None, driven_attr: pm.Attribute = None):
        self.curve: pm.PyNode = curve  # Can be either a Linear or Angular curve

        # anim curve interface
        self.input = self.curve.input
        self.output = self.curve.output

        self.driver: pm.PyNode = in_driver if in_driver is not None else self.init_driver()
        self.driven_attr: pm.Attribute = driven_attr if driven_attr is not None else self.init_driven_attr()

    @staticmethod
    def new_curve(pose_name: str, driven_attr: pm.Attribute, driver: pm.PyNode, pose_host_obj: pm.PyNode):
        is_angle = ct.is_attr_angular(driven_attr)
        curve_type = 'animCurveUU' if not is_angle else 'animCurveUA'
        new_curve_node = pm.createNode(curve_type)
        prefix = 'acUU' if not is_angle else 'acUA'
        curve_name = f'{prefix}_{pose_host_obj.getName()}_{pose_name}_{driven_attr.node()}_{driven_attr.shortName()}'
        new_curve_node.rename(curve_name)
        new_curve_node.addKey(0, 0)
        return DriverCurve(new_curve_node, driver, driven_attr)        

    def __str__(self) -> str:
        return f'{self.get_driven_obj_name()}.{self.get_driven_attr_name()}'

    def connect(self, target_attr):
        self.output.connect(target_attr)

    def get_num_keys(self) -> int:
        return self.curve.numKeys()

    def get_key_weight(self, key: int) -> float:
        return self.curve.getUnitlessInput(key)

    def get_key_val(self, key: int) -> float:
        if not self.is_curve_angle():
            return self.curve.getValue(key)
        else:
            return pu.degrees(self.curve.getValue(key))

    def get_key_idx_for_pose_weight(self, pose_weight: float) -> Optional[int]:
        """
        Returns None if key doesn't exist.
        Pose weight = time for a curve
        """
        tolerance = 0.1
        for i in range(0, self.curve.numKeys()):
            key_time = self.curve.getTime(i)
            if pose_weight - tolerance <= key_time <= pose_weight + tolerance:
                return i
        return None

    def capture_key(self, pose_weight: float):
        """
        Captures a key, that is to say it gets the pose weight as an input and reads the current driven attribute
        value from the scene.
        """
        attr_val = self.driven_attr.get()
        self.add_key(pose_weight, attr_val)

    def add_key(self, time: float, val: float) -> bool:
        """
        Adds a new key at the specified time (pose weight) and value (driver value). Converts to radians if the
        attribute is angular. Always call this function with degrees for angular attributes, not radians.
        """
        processed_val = val if not self.is_curve_angle() else pu.radians(val)
        self.curve.addKey(time, processed_val)
        return True

    def remove_key(self, idx: int):
        self.curve.remove(idx)

    def delete(self):
        """
        Kills itself, but it doesn't know anything about the rig or the connected attributes.
        """
        pm.delete(self.curve)
        self.input = None
        self.output = None
        self.driver = None
        self.driven_attr = None

    def nuke_keys(self):
        while self.curve.numKeys() > 0:
            self.remove_key(0)

    def try_change_key_weight(self, idx: int, new_weight: float) -> bool:
        if idx >= self.curve.numKeys():
            return False
        self.curve.setUnitlessInput(idx, new_weight)
        return True

    def try_change_key_value(self, idx: int, new_val: float) -> bool:
        processed_val = new_val if not self.is_curve_angle() else pu.radians(new_val)
        if idx >= self.curve.numKeys():
            return False
        self.curve.setValue(idx, processed_val)
        return True

    def get_name(self) -> str:
        return f'{self.get_driven_obj()}.{self.driven_attr.name(includeNode=False)}'

    def weight_to_str(self, idx: int) -> str:
        if idx >= self.curve.numKeys():
            return 'invalid index'
        return f'{self.curve.getUnitlessInput(idx):.2f}'

    def val_to_str(self, idx: int) -> str:
        val = self.curve.getValue(idx)
        processed_val = val if not self.is_curve_angle() else pu.degrees(val)
        if idx >= self.curve.numKeys():
            return 'invalid index'
        return f'{processed_val:.2f}'

    def is_curve_angle(self) -> bool:
        if 'acUA' in f'{self.curve}':
            return True
        return False

    def init_driven_attr(self) -> pm.Attribute:
        # This is the actual attribute that the curve is driving, not its plug on the driver node.
        driver = self.init_driver()
        obj_idx = self.output.listConnections(p=1)[0].index()

        if self.is_curve_angle():
            return driver.angularOutputs[obj_idx].listConnections(p=1)[0]
        else:
            return driver.linearOutputs[obj_idx].listConnections(p=1)[0]

    def get_driven_obj(self) -> pm.PyNode:
        if self.driven_attr is not None:
            return self.driven_attr.node()
        return None

    def get_driven_obj_name(self) -> str:
        return self.get_driven_obj().getName()

    def get_driven_attr_name(self) -> str:
        return self.driven_attr.name(includeNode=False)

    def init_driver(self):
        if self.driver is not None:
            return self.driver
        elif len(self.output.listConnections()) > 0:
            return self.output.listConnections()[0]
        return None

    def __eq__(self, __value: object) -> bool:
        if self.curve == __value.curve:
            return True
        return False
