import maya.api.OpenMaya as om

def get_mobject(node_name):
    
    if isinstance(node_name, om.MObject):
        return node_name
 
    if isinstance(node_name, om.MDagPath):
        return node_name.node()
 
    selection_list = om.MSelectionList()

    try:
        selection_list.add(node_name)
    except RuntimeError:
        assert False, 'The node: "'+node_name+'" could not be found.'
 
    num_matches = selection_list.length()
    assert (num_matches == 1), 'Multiple nodes found for the same name: '+node_name
 
    obj = selection_list.getDependNode(0)
    return obj


def get_mplug(obj, attribute):

    if not isinstance(obj, om.MObject):
        assert False, "expected MObject"

    dependency_node = om.MFnDependencyNode(obj)
    plug = om.MPlug()

    try:
        plug = dependency_node.findPlug( attribute, True)
    except RuntimeError:
        assert False, 'The attribute: "'+attribute+'" could not be found.'
           
    assert (not plug.isNull), 'The attribute: "'+attribute+'" could not be found.'

    return plug

def find_next_available_index(obj, plug_name):
    """
    Finds the next available logical index in an array plug. 
    obj can be str or MObject
    plug_name has to be str
    """
    if isinstance(obj, str):
        obj = get_mobject(obj)
    
    linear_plug : om.MPlug = get_mplug(obj, plug_name)
    num_elems = linear_plug.numElements()
    if num_elems == 0:
        return 0
    else:
        last_plug = linear_plug.elementByPhysicalIndex(num_elems - 1)
        last_logical_idx = last_plug.logicalIndex()
        return last_logical_idx + 1
