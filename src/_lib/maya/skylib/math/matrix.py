import maya.cmds as cmds
import pymel.core.datatypes as dt

UNREAL_BASIS = dt.Matrix((
    1, 0, 0, 0,
    0, 0, 1, 0,
    0, 1, 0, 0,
    0, 0, 0, 1
))


def get_matrix(obj_name: str, is_world: bool = True) -> dt.Matrix:
    return dt.Matrix(
        cmds.xform(obj_name, q=True, matrix=True, ws=is_world, os=not is_world)
    )


def change_basis(xform_matrix: dt.Matrix, new_basis: dt.Matrix = UNREAL_BASIS) -> dt.Matrix:
    return new_basis * xform_matrix * new_basis.inverse()
