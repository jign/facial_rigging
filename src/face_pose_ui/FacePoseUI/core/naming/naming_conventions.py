from FacePoseUI.core.side import Side


def get_side_from_name(obj) -> Side:
    obj_name = f'{obj}'
    if obj_name.startswith('l_'):
        return Side.LEFT
    if obj_name.startswith('r_'):
        return Side.RIGHT
    return Side.CENTER