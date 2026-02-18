from FaceJointGuides.core.component import Component
from FaceJointGuides.components.eye_judd.eye_judd_component import EyeJuddComponent
from FaceJointGuides.components.jaw.jaw_component import JawComponent
from FaceJointGuides.components.point_control.point_control_component import PointControlComponent
from FaceJointGuides.components.neck.neck_component import NeckComponent
from typing import List
import maya.api.OpenMaya as om2
import pymel.core as pm
from FaceJointGuides.core.names import *


COMPONENT_CLASSES = {
    'eye_judd': EyeJuddComponent,
    'point_control': PointControlComponent,
    "jaw": JawComponent,
}

def load_all_components() -> List[Component]:
    components: List[Component] = []

    point_control_comp = PointControlComponent()
    components.append(point_control_comp)

    neck_comp = NeckComponent()
    components.append(neck_comp)

    jaw_comp = JawComponent()
    components.append(jaw_comp)

    # Probably don't want the ear to the part of the face rig
    # ear_comp = EarComponent()
    # components.append(ear_comp)

    eye_comp = EyeJuddComponent()
    components.append(eye_comp)

    return components


def build_from_selection():
    """
    The contract is that the user has only selected one element, and it's a group
    :return:
    """
    selection: List = pm.ls(sl=1)
    if len(selection) == 0 or len(selection) > 1:
        om2.MGlobal.displayError('Please select only the top group of the guides')
        return
    selection: pm.PyNode = selection[0]
    if selection.getName() != FACIAL_GUIDES_GRP_NAME:
        om2.MGlobal.displayError('Please select only the top group of the guides')
        return

    top_rig_grp = pm.group(em=1, n=FACIAL_RIG_GRP_NAME)
    jnts_grp = pm.group(em=1, n=JNTS_GRP_NAME)
    face_rig_grp = pm.group(em=1, n=RIG_GRP_NAME)
    pm.parent(face_rig_grp, top_rig_grp)
    pm.parent(jnts_grp, top_rig_grp)

    # components can live under facial_guide_grp/<bucket>/...
    all_desc = selection.listRelatives(ad=True, type="transform") or []
    grp_components = [node for node in all_desc if node.hasAttr('comptype')]

    for comp in grp_components:
        comp_name: str = comp.comptype.get()
        COMPONENT_CLASSES[comp_name].build(comp)


def init_hierarchy():
    pm.group(em=1, n=FACIAL_GUIDES_GRP_NAME)


def _freeze_rot_scale_keep_translate(root: pm.PyNode) -> None:
    """
    Freeze rotations + scale (NOT translate) on `root` and all descendant transforms,
    while keeping their world-space translations unchanged.
    """
    nodes = [root] + (root.listRelatives(ad=True, type="transform") or [])

    # Freeze deepest nodes first to minimize parent->child compensation surprises.
    nodes.sort(key=lambda n: len(n.longName().split("|")), reverse=True)

    for n in nodes:
        try:
            ws_t = pm.xform(n, q=True, ws=True, t=True)
            pm.makeIdentity(n, apply=True, t=0, r=1, s=1, n=0)
            pm.xform(n, ws=True, t=ws_t)
        except Exception:
            # If a node can't be frozen (locked attrs, constraints, etc), skip it.
            pass

def _mirror_world_translate_across_yz(root: pm.PyNode) -> None:
    """
    Mirror a hierarchy across the YZ plane by flipping world X translation
    for every transform in the branch (root included).

    This avoids relying on parent negative scale (which can make children appear
    "unmirrored" in local channels and can get messy when freezing).
    """
    nodes = [root] + (root.listRelatives(ad=True, type="transform") or [])
    for n in nodes:
        try:
            ws_t = pm.xform(n, q=True, ws=True, t=True)
            ws_t[0] = -ws_t[0]
            pm.xform(n, ws=True, t=ws_t)
        except Exception:
            pass

def mirror_guides():
    if not pm.objExists(FACIAL_GUIDES_GRP_NAME):
        om2.MGlobal.displayError(f"Group '{FACIAL_GUIDES_GRP_NAME}' not found.")
        return

    guides_grp = pm.PyNode(FACIAL_GUIDES_GRP_NAME)

    # With the bucket layout (facial_guide_grp/<bucket>/l_*), left/right
    # branches are no longer direct children of facial_guide_grp.
    # Mirror the *top-most* l_/r_ transforms found anywhere under facial_guide_grp,
    # keeping them parented under the same parent (bucket) as the original.
    all_transforms = guides_grp.listRelatives(ad=True, type='transform') or []
    side_nodes = [n for n in all_transforms if n.nodeName().startswith('l_') or n.nodeName().startswith('r_')]

    top_side_nodes = []
    for node in side_nodes:
        node_name = node.nodeName()
        prefix = 'l_' if node_name.startswith('l_') else 'r_'

        parent = node.getParent()
        is_nested_under_same_side = False
        while parent is not None and parent != guides_grp:
            parent_name = parent.nodeName()
            if parent_name.startswith(prefix):
                is_nested_under_same_side = True
                break
            parent = parent.getParent()

        if not is_nested_under_same_side:
            top_side_nodes.append(node)

    for node in sorted(top_side_nodes, key=lambda n: n.longName()):
        original_name = node.nodeName()

        if original_name.startswith('l_'):
            source_prefix = 'l_'
            target_prefix = 'r_'
        elif original_name.startswith('r_'):
            source_prefix = 'r_'
            target_prefix = 'l_'
        else:
            continue

        target_name = original_name.replace(source_prefix, target_prefix, 1)

        original_parent = node.getParent()
        if original_parent is None:
            continue

        # Check if target already exists *under the same parent*
        siblings = original_parent.listRelatives(c=True, type='transform') or []
        if any(sib.nodeName() == target_name for sib in siblings):
            continue

        # Duplicate branch
        new_nodes = pm.duplicate(node, rc=True)
        root_duplicate = new_nodes[0]

        # Rename hierarchy
        root_duplicate.rename(target_name)

        descendants = root_duplicate.listRelatives(ad=True, type='transform') or []
        for desc in descendants:
            desc_name = desc.nodeName()

            # Strip trailing digits Maya may add during duplication
            clean_name = desc_name.rstrip('0123456789')

            if clean_name.startswith(source_prefix):
                new_desc_name = clean_name.replace(source_prefix, target_prefix, 1)
                desc.rename(new_desc_name)

        # # Mirror across YZ plane by negative X scale on a temp group.
        # temp_grp = pm.group(em=True)
        # pm.parent(root_duplicate, temp_grp)
        # temp_grp.sx.set(-1)

        # pm.parent(root_duplicate, original_parent)
        # pm.delete(temp_grp)

        # # NEW: freeze rotate + scale so you end up with rotate=0 and scale=1,
        # # while keeping translations intact for later tx/ty/tz reads.
        # _freeze_rot_scale_keep_translate(root_duplicate)        

        # Mirror in world by flipping X translation for the whole branch (root + children).
        _mirror_world_translate_across_yz(root_duplicate)

        # Freeze rotate + scale so you end up with rotate=0 and scale=1,
        # while keeping translations intact for later tx/ty/tz reads.
        _freeze_rot_scale_keep_translate(root_duplicate)

        om2.MGlobal.displayInfo(f"Mirrored {original_name} to {target_name}")