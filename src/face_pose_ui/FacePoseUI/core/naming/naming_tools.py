from FacePoseUI.core.side import Side


# TODO I may want to move these to skybloom core

# We're hardcoding the left and right prefixes here since these are studio conventions.
# We're also hardcoding side prefixes.
# If we wanted to either release the tool to the public, or if we need different conventions later, we have to change these.


def get_mirrored_name(name: str) -> str:
    if name.startswith('l_'):
        return name.replace('l_', 'r_', 1)
    elif name.startswith('r_'):
        return name.replace('r_', 'l_', 1)
    return name


def get_side(obj) -> Side:
    obj_name = f'{obj}'
    if obj_name.startswith('l_'):
        return Side.LEFT
    if obj_name.startswith('r_'):
        return Side.RIGHT
    return Side.CENTER


def get_side_as_str(obj) -> str:
    side = get_side(obj)
    if side == Side.LEFT:
        return 'left'
    elif side == Side.RIGHT:
        return 'right'
    elif side == Side.CENTER:
        return 'center'
    return 'none'
