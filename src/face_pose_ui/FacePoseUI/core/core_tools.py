import pymel.core as pm
import maya.cmds as cmds
import maya.api.OpenMaya as om
from typing import Optional
import skylib.utils.core_utils as sc


def is_attr_linear(attr : pm.Attribute) -> bool:
    """
    Determine if a Maya attribute is of a linear type (float or distance).
    Linear attributes are those that represent continuous numerical values that
    can be interpolated linearly, such as translation attributes or float/double numeric types.
    Parameters:
        attr (pm.Attribute): The PyMel attribute to check
    Returns:
        bool: True if the attribute is of a linear type, False otherwise
    """
    mplug = om.MSelectionList().add(attr.name()).getPlug(0)
    mobj = mplug.attribute()
    
    # Check for numeric attribute types
    if mobj.hasFn(om.MFn.kNumericAttribute):
        fn_attr = om.MFnNumericAttribute(mobj)
        # Linear attributes are typically float or double
        return fn_attr.unitType() in (om.MFnNumericData.kFloat, om.MFnNumericData.kDouble)
    
    # Check for unit attribute types
    elif mobj.hasFn(om.MFn.kUnitAttribute):
        fn_unit_attr = om.MFnUnitAttribute(mobj)
        # Check for distance (translation) or scale units
        return fn_unit_attr.unitType() == om.MFnUnitAttribute.kDistance
    
    return False


def is_attr_angular(attr : pm.Attribute) -> bool:
    """
    Determines if a Maya attribute is of angular (rotation) type.
    This function checks if the given Maya attribute represents an angle by examining
    if it's a unit attribute with the angle unit type.
    Args:
        attr (pm.Attribute): A PyMel attribute to check.
    Returns:
        bool: True if the attribute is of angular type, False otherwise.
    Examples:
        >>> is_attr_angular(pm.PyNode("pSphere1.rotateX"))
        True
        >>> is_attr_angular(pm.PyNode("pSphere1.translateX"))
        False
    """
    mplug = om.MSelectionList().add(attr.name()).getPlug(0)
    mobj = mplug.attribute()
    
    # Check for unit attribute types
    if mobj.hasFn(om.MFn.kUnitAttribute):
        fn_unit_attr = om.MFnUnitAttribute(mobj)
        # Check for angle units
        return fn_unit_attr.unitType() == om.MFnUnitAttribute.kAngle

    return False


def get_driven_linear_attribute_index(driver, attr: pm.Attribute) -> Optional[int]:
    linear_connected_objs = pm.listConnections(
        f'{driver}.linearOutputs',
        plugs=True
    ) or []
    for conn_attr in linear_connected_objs:
        if conn_attr == attr:
            return attr.inputs(p=1)[0].item()
    return None


def get_driven_angular_attribute_index(driver, attr: pm.Attribute) -> Optional[int]:
    angular_conns = pm.listConnections(
        f'{driver}.angularOutputs',
        plugs=True
    ) or []
    for conn_attr in angular_conns:
        if conn_attr == attr:
            return attr.inputs(p=1)[0].item()
    return None


def get_driven_objs_for_driver(driver):
    """
    Returns a dictionary with objects as keys and attributes as values.
    For example, if "l_brow_inner" is the object, then "tx, ty, ..." are the attributes
    But, I think... keeping them as raw objects is still better, even using the same
    Key:Value storage
    """
    driven_dict = {}  # object -> [attributes]

    linear_outputs: pm.Attribute = pm.Attribute(f'{driver}.linearOutputs')
    angular_outputs: pm.Attribute = pm.Attribute(f'{driver}.angularOutputs')

    linear_connected_objs = set(linear_outputs.listConnections())
    angular_connected_objs = set(angular_outputs.listConnections())

    linear_conns = linear_outputs.listConnections(p=1)
    angular_conns = angular_outputs.listConnections(p=1)

    driven_objs = linear_connected_objs.union(angular_connected_objs)
    if len(driven_objs) > 0:
        for obj in driven_objs:
            driven_dict[obj] = []

    for conn_attr in linear_conns:
        driven_dict[conn_attr.node()].append(conn_attr)
    for conn_attr in angular_conns:
        driven_dict[conn_attr.node()].append(conn_attr)

    return driven_dict


def get_linear_outputs_plug(driver) -> om.MPlug:
    linear_plug: om.MPlug = sc.get_mplug(get_driver_as_mobj(driver), 'linearOutputs')
    return linear_plug


def get_angular_outputs_plug(driver) -> om.MPlug:
    angular_plug: om.MPlug = sc.get_mplug(get_driver_as_mobj(driver), 'angularOutputs')
    return angular_plug


def get_driver_as_mobj(driver) -> om.MObject:
    driver_obj: om.MObject = sc.get_mobject(f'{driver}')
    return driver_obj


def find_next_available_linear_index(driver) -> int:
    """
    determines the output index to make a connection to a driven attribute
    """
    linear_plug: om.MPlug = get_linear_outputs_plug(driver)
    num_elems = linear_plug.numElements()
    if num_elems == 0:
        return 0
    else:
        last_plug = linear_plug.elementByPhysicalIndex(num_elems - 1)
        last_logical_idx = last_plug.logicalIndex()
        return last_logical_idx + 1


def find_next_available_angular_index(driver) -> int:
    """
    determines the output index to make a connection to a driven attribute
    """
    angular_plug: om.MPlug = get_angular_outputs_plug(driver)
    num_elems = angular_plug.numElements()
    if num_elems == 0:
        return 0
    else:
        last_plug = angular_plug.elementByPhysicalIndex(num_elems - 1)
        last_logical_idx = last_plug.logicalIndex()
        return last_logical_idx + 1


def force_refresh_driver_conns(driver):
    """
    done possibly because of a bug in my plugin code
    possibly already fixed with setDependentsDirty implementation in the plugin
    """
    conn_list = cmds.listConnections(f'{driver}', p=1, c=1)
    if conn_list is not None and len(conn_list) > 0:
        filtered_list = [conn for conn in conn_list if 'output' in conn]
        for conn in filtered_list:
            obj = conn.split('.')[0]
            pn = pm.PyNode(obj)
            pn.attr(conn.split('.')[1]).get()  # Force a refresh on the array element


def unplug_attr(driver, attr: pm.Attribute):
    if is_attr_linear(attr):
        attr_idx = get_driven_linear_attribute_index(driver, attr)
        driver.linearOutputs[attr_idx].disconnect()
    else:
        attr_idx = get_driven_angular_attribute_index(driver, attr)
        driver.angularOutputs[attr_idx].disconnect()        


def clean_plug_from_driver(rig, attr: pm.Attribute):
    """
    Called, for example, when a subpose is deleted. Checks if the plug for the attribute has any connections?
    At this point the plug will be connected even if there are no subposes driving that plug. I need to find out if
    I should disconnect the plug. How?
    """
    if not rig.is_rig_driving_attr(attr):
        unplug_attr(rig.driver, attr)

  