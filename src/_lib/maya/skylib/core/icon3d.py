from pymel.core import datatypes as dt
import pymel.core as pm
import math
import maya.api.OpenMaya as om
from typing import List, Optional, Union
from skylib.core.curve import *
from skylib.math.point import *


def make_cube(size: float = 1, name: str = 'cube'):
    lenX = size * 0.5
    lenY = size * 0.5
    lenZ = size * 0.5

    # p is positive, N is negative
    ppp = dt.Vector(lenX, lenY, lenZ)
    ppN = dt.Vector(lenX, lenY, lenZ * -1)
    pNp = dt.Vector(lenX, lenY * -1, lenZ)
    Npp = dt.Vector(lenX * -1, lenY, lenZ)
    pNN = dt.Vector(lenX, lenY * -1, lenZ * -1)
    NNp = dt.Vector(lenX * -1, lenY * -1, lenZ)
    NpN = dt.Vector(lenX * -1, lenY, lenZ * -1)
    NNN = dt.Vector(lenX * -1, lenY * -1, lenZ * -1)

    points = [ppp, ppN, NpN, NNN, NNp, Npp, NpN, Npp, ppp, pNp, NNp, pNp, pNN,
           ppN, pNN, NNN]

    node = create_curve(name, points, close=False, degree=1)

    return node


def make_x(width: float = 1, name: str = "x"):
    width = width * 0.35
    offset1 = width * .5
    offset2 = width * 1.5

    v0 = dt.Vector(width, offset2, 0)
    v1 = dt.Vector(offset2, width, 0)
    v2 = dt.Vector(offset1, 0, 0)

    v3 = dt.Vector(offset2, -width, 0)
    v4 = dt.Vector(width, -offset2, 0)
    v5 = dt.Vector(0, -offset1, 0)

    v6 = dt.Vector(-width, -offset2, 0)
    v7 = dt.Vector(-offset2, -width, 0)
    v8 = dt.Vector(-offset1, 0, 0)

    v9 = dt.Vector(-offset2, width, 0)
    v10 = dt.Vector(-width, offset2, 0)
    v11 = dt.Vector(0, offset1, 0)

    points = [v0, v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11]

    node = create_curve(name, points, close=True, degree=1)

    return node


def make_cross(width: float = 1, name: str = "cross"):
    dlen = width * .5

    v0 = dt.Vector(dlen, 0, 0)
    v1 = dt.Vector(-dlen, 0, 0)
    v2 = dt.Vector(0, dlen, 0)
    v3 = dt.Vector(0, -dlen, 0)
    v4 = dt.Vector(0, 0, dlen)
    v5 = dt.Vector(0, 0, -dlen)

    points = [v0, v1]
    node = create_curve(name, points, close=False, degree=1)

    points = [v2, v3]
    crv_0 = create_curve(name + 'crv_0', points, close=False, degree=1)

    points = [v4, v5]
    crv_1 = create_curve(name + 'crv_1', points, close=False, degree=1)

    for crv in [crv_0, crv_1]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    return node


def make_compass(width: float = 1, name: str = "compass"):
    dlen = width * 0.5

    division = 24

    point_pos = []
    v = dt.Vector(0, 0, dlen)

    for i in range(division):
        if i == division / 2:
            w = dt.Vector(v.x, v.y, v.z - dlen * .4)
        else:
            w = dt.Vector(v.x, v.y, v.z)
        point_pos.append(w)
        v = v.rotateBy((0, (2 * math.pi) / (division + 0.0), 0))

    points = point_pos
    node = create_curve(name, points, close=True, degree=3)
    return node


def make_ball(width: float = 1, name: str = "ball"):
    dlen = width * .5

    v0 = dt.Vector(0, 0, -dlen * 1.108)
    v1 = dt.Vector(dlen * .78, 0, -dlen * .78)
    v2 = dt.Vector(dlen * 1.108, 0, 0)
    v3 = dt.Vector(dlen * .78, 0, dlen * .78)
    v4 = dt.Vector(0, 0, dlen * 1.108)
    v5 = dt.Vector(-dlen * .78, 0, dlen * .78)
    v6 = dt.Vector(-dlen * 1.108, 0, 0)
    v7 = dt.Vector(-dlen * .78, 0, -dlen * .78)

    points = [v0, v1, v2, v3, v4, v5, v6, v7]
    node = create_curve(name, points, close=True, degree=3)

    ro = dt.Vector([math.pi/2, 0, 0])
    points = offset_points([v0, v1, v2, v3, v4, v5, v6, v7], rot_offset=ro)
    crv_0 = create_curve(node + "_0crv", points, close=True, degree=3)

    ro = dt.Vector([math.pi, 0, math.pi/2])
    points = offset_points([v0, v1, v2, v3, v4, v5, v6, v7], rot_offset=ro)
    crv_1 = create_curve(node + "_1crv", points, close=True, degree=3)

    for crv in [crv_0, crv_1]:
        for shp in crv.listRelatives(shapes=True):
            node.addChild(shp, add=True, shape=True)
        pm.delete(crv)

    return node


def make_crossball(size: float = 1, name: str = 'crossball', color: Optional[Union[int, List[float]]] = None) -> pm.PyNode:
    crossball = make_ball(size, name)
    cross = make_cross(size * 2, name + "cross")
    for shp in cross.listRelatives(shapes=True):
        crossball.addChild(shp, add=True, shape=True)
    pm.delete(cross)
    if color is not None:
        set_color(crossball, color)
    return crossball


def make_crosscube(size: float = 1, name: str = 'crosscube', color: Optional[Union[int, List[float]]] = None) -> pm.PyNode:
    crosscube = make_cube(size, name)
    cross = make_cross(size * 2.5, name + "cross")
    for shp in cross.listRelatives(shapes=True):
        crosscube.addChild(shp, add=True, shape=True)
    pm.delete(cross)
    if color is not None:
        set_color(crosscube, color)
    return crosscube


def make_ghostline(name: str, controls: List[pm.PyNode]) -> pm.PyNode:
    ghostline = create_control_line(name, controls)
    ghostline.overrideEnabled.set(True)
    ghostline.overrideDisplayType.set(1)
    return ghostline
