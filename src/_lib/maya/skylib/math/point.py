from pymel.core import datatypes as dt
import pymel.core as pm
import maya.api.OpenMaya as om
from typing import List, Optional


def offset_points(
        points: List[dt.Vector],
        pos_offset: Optional[dt.Vector] = None,
        rot_offset: Optional[dt.Vector] = None) -> List[dt.Vector]:
    """
    Offset a list of points
    Arguments:
        points (list of vector): Point positions.
        pos_offset (vector):  The position offset of the curve from its
            center.
        rot_offset (vector): The rotation offset of the curve from its
            center. In radians.

    Returns:
        list of vector: the new point positions

    """
    pts: List[dt.Vector] = []
    for v in points:
        if rot_offset:
            mv = om.MVector(v.x, v.y, v.z)
            mv = mv.rotateBy(om.MEulerRotation(rot_offset.x,
                                               rot_offset.y,
                                               rot_offset.z,
                                               om.MEulerRotation.kXYZ))
            v = dt.Vector(mv.x, mv.y, mv.z)
        if pos_offset:
            v = v + pos_offset

        pts.append(v)

    return pts
