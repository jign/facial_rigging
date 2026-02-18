import pymel.core as pm
import maya.cmds as mc
from typing import List


def move_to_origin(obj: pm.PyNode):
    pm.move(obj, [0, 0, 0], rpr=True)


def set_pivot(obj: pm.PyNode, pivot_location: List[float]):
    pm.xform(obj, ws=True, piv=pivot_location)


def lock_all_keyable_attributes(obj: pm.PyNode):
    keyable_attrs = obj.listAttr(keyable=True)
    for attr in keyable_attrs:
        try:
            attr.set(lock=True)
        except RuntimeError as e:
            print(f"Failed to lock attribute {attr}: {e}")


def get_top_node(obj: pm.PyNode) -> pm.PyNode:
    top_node: pm.PyNode = obj
    while top_node.getParent():
        top_node = top_node.getParent()
    return top_node


def get_world_position(obj: pm.PyNode) -> List[float]:
    return pm.xform(obj, q=True, ws=True, t=True)


def get_scene_name() -> str:
    return pm.system.sceneName().basename()
