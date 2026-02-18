from FacePoseUI.core.rig import Rig
from FacePoseUI.core.pose import Pose
from FacePoseUI.core.pose import Subpose
import FacePoseUI.ui_control.pose_context as posec
import FacePoseUI.core.naming.naming_tools as nt
import pymel.core as pm
from pathlib import Path
from typing import Dict, List
import json

SERIALIZATION_VERSION = "1.1.0"


class RigSerializer:
    def __init__(self, path: Path, rig: Rig):
        self.path: Path = path
        self.rig: Rig = rig

    def serialize_rig(self):
        if not self.validate():
            pm.warning("Cannot serialize rig")
            return
        
        serialized_rig = {
            'version': SERIALIZATION_VERSION,
            'driver': self.rig.driver.getName()
            }

        self.serialize_controls(serialized_rig)
        self.serialize_all_poses(serialized_rig)

        self.save_to_json(serialized_rig)

    def serialize_controls(self, serialized_dict) -> Dict:
        controls = {}
        for control_object in self.rig.get_control_objects():
            ctrl_name = control_object.getName()
            ctrl_dict = {
                "side": nt.get_side_as_str(control_object),
                "poses": {}
            }
            controls[ctrl_name] = ctrl_dict

        serialized_dict['controls'] = controls
        return serialized_dict

    def serialize_all_poses(self, serialized_dict) -> Dict:
        for pose in self.rig.get_poses():
            pose_host = pose.get_host_obj_name()
            pose_name = pose.get_pose_name()
            pose_dict = self.get_dict_for_pose(pose)

            serialized_dict['controls'][pose_host]['poses'][pose_name] = pose_dict

        return serialized_dict

    def get_dict_for_pose(self, pose: Pose) -> Dict:
        pose_dict = {
            'min_val': pose.get_min_val(),
            'max_val': pose.get_max_val(),
            'subposes': self.get_subposes_dict(pose)
        }

        return pose_dict

    def get_subposes_dict(self, pose: Pose) -> Dict:
        subposes_dict = {}

        for subpose in pose.subposes:
            subpose_name = subpose.get_name()
            subposes_dict[subpose_name] = {
                "attr_type": subpose.get_driven_attr_type(),
                "keys": self.get_subpose_keys(subpose)
            }

        return subposes_dict

    def get_subpose_keys(self, subpose: Subpose) -> List:
        keys = []

        for i in range(0, subpose.get_num_keys()):
            key_dict = {
                "pose_weight": subpose.get_key_weight(i),
                "val": subpose.get_key_val(i)
            }
            keys.append(key_dict)

        return keys

    def save_to_json(self, serialized_rig):
        with open(self.path, "w") as outfile:
            json.dump(serialized_rig, outfile, indent=4)

    def validate(self) -> bool:
        """Validate that all required components are available for serialization."""
        if not self.path:
            pm.warning("Cannot serialize: No output path specified")
            return False
            
        if not self.rig:
            pm.warning("Cannot serialize: No rig specified")
            return False
            
        if not self.rig.driver:
            pm.warning("Cannot serialize: Rig has no driver")
            return False
            
        if not self.rig.get_control_objects():
            pm.warning("Cannot serialize: Rig has no control objects")
            return False
            
        return True


class RigDeserializer:
    def __init__(self, path: Path, rig: Rig):
        self.serialized_dict = self.load_dict_from_path(path)
        self.rig = rig

    @staticmethod
    def load_dict_from_path(path: Path) -> Dict:
        with open(path, 'r') as fp:
            return json.load(fp)

    def load_rig(self):
        for control_name in self.serialized_dict["controls"]:
            host_obj = pm.PyNode(control_name)

            poses = self.serialized_dict["controls"][control_name]["poses"]
            for pose_name in poses:
                pose_dict = self.serialized_dict["controls"][control_name]["poses"][pose_name]
                min_val = pose_dict['min_val']
                max_val = pose_dict['max_val']
                pose = posec.new_pose(self.rig, host_obj, pose_name, min_val, max_val)

                for subpose_name in pose_dict['subposes']:
                    subpose_dict = pose_dict['subposes'][subpose_name]
                    driven_attr = pm.Attribute(subpose_name)
                    subpose = self.rig.add_subposes_to_pose(pose, driven_attr)[0]

                    keys = subpose_dict['keys']
                    for key in keys:
                        key_weight = key['pose_weight']
                        key_val = key['val']
                        subpose.add_key(key_weight, key_val)

    def rebuild_rig(self):
        driver_name = self.serialized_dict['driver']
            
        # Check if a Maya node with the driver name already exists
        if pm.objExists(driver_name):
            pm.warning(f"Driver node '{driver_name}' already exists. Cannot rebuild rig.")
            return
        
        # Create the driver node
        driver = pm.createNode('facePoseDriver', name=driver_name)
        self.rig.set_driver(driver)
        
        # Load the rest of the rig
        self.load_rig()