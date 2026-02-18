import pymel.core as pm
from pymel.core import datatypes as dt
import maya.api.OpenMaya as om2
from typing import List, Union


def create_curve(
        name: str,
        points: List[dt.Vector],
        parent: pm.PyNode = None,
        close: bool = False,
        degree: int = 3,
        global_transform: dt.Matrix = dt.Matrix()) -> pm.PyNode:
    if close:
        points.extend(points[:degree])
        knots = range(len(points) + degree - 1)
        node = pm.curve(n=name, d=degree, p=points, per=close, k=knots)
    else:
        node = pm.curve(n=name, d=degree, p=points)

    if global_transform is not None:
        node.setTransformation(global_transform)

    if parent is not None:
        parent.addChild(node)

    return node


def create_control_line(name: str, controls: List[pm.PyNode], parent: pm.PyNode = None, degree: int = 1):
    # rebuild list to avoid input list modification
    centers = controls[:]
    if degree == 3:
        if len(centers) == 2:
            centers.insert(0, centers[0])
            centers.append(centers[-1])
        elif len(centers) == 3:
            centers.append(centers[-1])

    points = [dt.Vector() for center in centers]

    node = create_curve(name, points, parent, False, degree)

    pm.select(node)
    deformer_node = pm.deformer(type="mgear_curveCns")[0]

    for i, item in enumerate(centers):
        pm.connectAttr(item + ".worldMatrix", deformer_node + ".inputs[%s]" % i)

    return node


def set_color(curve: pm.PyNode, color: Union[int, List[float]]):
    if isinstance(color, int):
        for shape in curve.listRelatives(shapes=True):
            shape.overrideEnabled.set(True)
            shape.overrideColor.set(color)
    else:
        for shape in curve.listRelatives(shapes=True):
            shape.overrideEnabled.set(True)
            shape.overrideRGBColors.set(True)
            shape.overrideColorRGB.set(color[0], color[1], color[2])

