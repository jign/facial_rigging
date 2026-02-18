import pymel.core as pm
from FacePoseUI.core.driver_curve import DriverCurve
import FacePoseUI.core.core_tools as ct


class Subpose:
    def __init__(self, in_driver_curve):
        self.driver_curve: DriverCurve = in_driver_curve

    @staticmethod
    def new_subpose(pose_name: str, pose_attr: pm.Attribute, driven_attr: pm.Attribute, driver: pm.PyNode, rig, pose_idx: int):
        pose_host_obj = pose_attr.node()
        new_curve = DriverCurve.new_curve(pose_name, driven_attr, driver, pose_host_obj)
        pose_attr.connect(new_curve.input)

        if not new_curve.is_curve_angle():
            driver_idx_for_driven_attr = ct.get_driven_linear_attribute_index(rig.driver, driven_attr)
            new_curve.output.connect(driver.poses[pose_idx].linearSubposes[driver_idx_for_driven_attr])
        else:
            driver_idx_for_driven_attr = ct.get_driven_angular_attribute_index(rig.driver, driven_attr)
            new_curve.output.connect(driver.poses[pose_idx].angularSubposes[driver_idx_for_driven_attr])

        return Subpose(new_curve)        

    def get_name(self) -> str:
        return self.driver_curve.get_name()

    def get_num_keys(self) -> int:
        return self.driver_curve.get_num_keys()

    def get_driven_object(self) -> pm.PyNode:
        return self.driver_curve.get_driven_obj()

    def get_driven_obj_name(self) -> str:
        return self.driver_curve.get_driven_obj_name()

    def get_driven_attr(self) -> pm.Attribute:
        return self.driver_curve.driven_attr

    def get_driven_attr_type(self) -> str:
        """
        Returns the type (linear or angular) as a string
        :return:
        """
        if self.driver_curve.is_curve_angle():
            return 'angular'
        else:
            return 'linear'

    def capture_key(self, pose_weight: float):
        self.driver_curve.capture_key(pose_weight)

    def set_key(self, pose_weight: float, val: float):
        key_idx = self.driver_curve.get_key_idx_for_pose_weight(pose_weight)
        if key_idx is None:
            self.driver_curve.add_key(pose_weight, val)
        else:
            self.driver_curve.try_change_key_value(key_idx, val)

    def remove_key(self, key_idx: int):
        self.driver_curve.remove_key(key_idx)

    def add_key(self, pose_weight: float, attr_val: float):
        return self.driver_curve.add_key(pose_weight, attr_val)

    def try_change_key_weight(self, key_idx: int, new_weight: float):
        self.driver_curve.try_change_key_weight(key_idx, new_weight)

    def try_change_key_value(self, key_idx: int, new_val: float):
        self.driver_curve.try_change_key_value(key_idx, new_val)

    def delete(self):
        """
        This doesn't handle unplugging the driver node, probably?
        """
        self.driver_curve.delete()
        self.driver_curve = None

    def weight_to_str(self, key_idx: int) -> str:
        return self.driver_curve.weight_to_str(key_idx)

    def get_key_weight(self, key_idx: int) -> float:
        return self.driver_curve.get_key_weight(key_idx)

    def val_to_str(self, key_idx: int) -> str:
        return self.driver_curve.val_to_str(key_idx)

    def get_key_val(self, key_idx: int) -> float:
        return self.driver_curve.get_key_val(key_idx)

    def __eq__(self, __value: object) -> bool:
        # TODO check class? Can I do that? Same for DriverCurve __eq__
        if f'{self.driver_curve}' == f'{__value.driver_curve}':
            return True
        return False
