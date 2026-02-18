from FaceJointGuides.core.component import Component
import skylib.core.icon3d as i3d
import pymel.core as pm
import maya.api.OpenMaya as om2


class JawComponent(Component):
    def __init__(self):
        super().__init__()
        self._name = "jaw"

    def draw(self):
        jaw = i3d.make_crosscube(1, 'jaw_guide', [1.0, 0.0, 0.0])
        jaw_grp = pm.group(em=1, n='jaw_grp')
        self.add_global_attrs(jaw_grp)

        # organize hierarchy -- ghostlines are visuals are for development only, to help guide the placement
        ghostline_grp = pm.group(em=1, n='jaw_ghostline_grp')
        visuals_grp = pm.group(em=1, n='jaw_visuals_grp')

        # controls group for individual jaw-driven point controls, so that they not only follow the head, but also the jaw -- these should be point controls
        controls_grp = pm.group(em=1, n='jaw_controls_grp')

        pm.parent(jaw, jaw_grp)
        pm.parent(ghostline_grp, jaw_grp)
        pm.parent(visuals_grp, jaw)
        pm.parent(controls_grp, jaw_grp)

        # Visual guides (NO JOINTS should be created for these)
        visual_guide_a = i3d.make_crossball(1, 'jaw_visual_guide_a', [1.0, 1.0, 0.0])
        pm.parent(visual_guide_a, visuals_grp)
        visual_guide_b = i3d.make_crossball(1, 'jaw_visual_guide_b', [1.0, 1.0, 0.0])
        pm.parent(visual_guide_b, visuals_grp)

        ghostline = i3d.make_ghostline('jaw_ghostline', [jaw, visual_guide_a, visual_guide_b])
        pm.parent(ghostline, ghostline_grp)
        
        return jaw_grp
    
    @staticmethod
    def _snap_transform(dst: pm.PyNode, src: pm.PyNode) -> None:
        """Match dst to src (world pos + rot) without leaving constraints behind."""
        try:
            pt = pm.pointConstraint(src, dst)
            orc = pm.orientConstraint(src, dst)
            pm.delete(pt, orc)
        except Exception:
            pass

    @staticmethod
    def _find_direct_child(parent: pm.PyNode, child_name: str) -> pm.PyNode | None:
        children = parent.listRelatives(c=True, type="transform") or []
        for ch in children:
            if ch.nodeName() == child_name:
                return ch
        return None

    @staticmethod
    def _iter_point_guides(controls_root: pm.PyNode) -> list[pm.PyNode]:
        """
        Heuristic: any transform under controls_root that has shapes is treated as a jaw point guide.
        """
        nodes = controls_root.listRelatives(ad=True, type="transform") or []
        out: list[pm.PyNode] = []
        for n in nodes:
            if n is None:
                continue
            if n.nodeName().endswith("_grp"):
                continue
            # ignore any accidental visuals/ghostlines under controls
            if "ghost" in n.nodeName().lower() or "visual" in n.nodeName().lower():
                continue
            try:
                if n.getShapes():
                    out.append(n)
            except Exception:
                continue
        # also include direct children that might not be returned as ad=True in some cases
        for n in (controls_root.listRelatives(c=True, type="transform") or []):
            if n not in out:
                try:
                    if n.getShapes() and not n.nodeName().endswith("_grp"):
                        out.append(n)
                except Exception:
                    pass
        # stable order
        out.sort(key=lambda x: x.longName())
        return out    

    @staticmethod
    def build(guide: pm.PyNode):
        """
        Expected guide layout under facial_guide_grp/<bucket>/jaw_grp:
          jaw_grp
            jaw_guide               (pivot / main jaw guide)
            jaw_controls_grp        (point guides that DO create joints)
            jaw_visuals_grp         (visual-only guides; ignored)
        """
        # bucket-based intermediate parents
        target_jnts_parent = Component.get_intermediate_jnts_grp(guide)
        target_rig_parent = Component.get_intermediate_rig_grp(guide)

        jaw_guide = JawComponent._find_direct_child(guide, "jaw_guide")
        if jaw_guide is None:
            om2.MGlobal.displayError("Jaw build: expected a child named 'jaw_guide' under jaw_grp.")
            return

        controls_grp = JawComponent._find_direct_child(guide, "jaw_controls_grp")
        if controls_grp is None:
            om2.MGlobal.displayError("Jaw build: expected a child named 'jaw_controls_grp' under jaw_grp.")
            return

        # rig organization under the same bucket as the jaw
        jaw_rig_grp_name = "jaw_rig_grp"
        if pm.objExists(jaw_rig_grp_name):
            om2.MGlobal.displayError(f"Jaw build: '{jaw_rig_grp_name}' already exists. Delete it and rebuild.")
            return
        jaw_rig_grp = pm.group(em=True, n=jaw_rig_grp_name)
        pm.parent(jaw_rig_grp, target_rig_parent)

        # --- main jaw joint + jaw locator controller ---
        jaw_pos = jaw_guide.getTranslation(space="world")

        jaw_jnt_name = "jaw_jnt_anim"
        if pm.objExists(jaw_jnt_name):
            om2.MGlobal.displayError(f"Jaw build: joint '{jaw_jnt_name}' already exists. Delete it and rebuild.")
            return
        jaw_jnt = pm.joint(target_jnts_parent, n=jaw_jnt_name, p=jaw_pos)

        jaw_ctrl_name = "jaw_ctrl"
        if pm.objExists(jaw_ctrl_name):
            om2.MGlobal.displayError(f"Jaw build: locator '{jaw_ctrl_name}' already exists. Delete it and rebuild.")
            return

        jaw_ctrl = pm.spaceLocator(n=jaw_ctrl_name)
        jaw_ctrl_grp = pm.group(jaw_ctrl, n=f"{jaw_ctrl_name}_grp")

        JawComponent._snap_transform(jaw_ctrl_grp, jaw_jnt)
        try:
            pm.makeIdentity(jaw_ctrl_grp, apply=True, t=1, r=1, s=1, n=0)
        except Exception:
            pass

        pm.parent(jaw_ctrl_grp, jaw_rig_grp)

        pm.parentConstraint(jaw_ctrl, jaw_jnt, mo=True)
        pm.scaleConstraint(jaw_ctrl, jaw_jnt)

        # --- point controls: joints under bucket jnts, locators under bucket rig,
        # but locator *drivers* follow the jaw ctrl via a follow group constraint ---
        point_guides = JawComponent._iter_point_guides(controls_grp)

        if not point_guides:
            om2.MGlobal.displayWarning("Jaw build: no point guides found under jaw_controls_grp.")
            return

        for pg in point_guides:
            pg_name = pg.nodeName()
            pg_pos = pg.getTranslation(space="world")

            try:
                pg_scale = pm.xform(pg, q=True, s=True, ws=False)
            except Exception:
                pg_scale = [1.0, 1.0, 1.0]
            # use a single scalar for joint radius (average of components)
            pg_scale_avg = sum(pg_scale) / 3.0

            # joints live under bucket intermediate jnts group (NOT under jaw_jnt)
            jnt_name = f"{pg_name}_jnt_anim"
            if pm.objExists(jnt_name):
                om2.MGlobal.displayWarning(f"Jaw build: '{jnt_name}' exists; skipping.")
                continue
            jnt = pm.joint(target_jnts_parent, n=jnt_name, p=pg_pos)
            # set joint radius to match guide scale
            try:
                jnt.radius.set(pg_scale_avg)
            except Exception:
                try:
                    pm.setAttr(f"{jnt}.radius", pg_scale_avg)
                except Exception:
                    pass            

            # locator driver hierarchy under the jaw rig group
            follow_grp = pm.group(em=True, n=f"{pg_name}_follow_grp")
            pm.xform(follow_grp, ws=True, t=[pg_pos.x, pg_pos.y, pg_pos.z])
            pm.parent(follow_grp, jaw_rig_grp)

            # Make the whole point-control driver follow the jaw controller (open/close)
            pm.parentConstraint(jaw_ctrl, follow_grp, mo=True)

            # Offset group + locator that actually drives the joint
            loc_name = f"{pg_name}_ctrl"
            loc = pm.spaceLocator(n=loc_name)
            loc_grp = pm.group(loc, n=f"{loc_name}_grp")
            JawComponent._snap_transform(loc_grp, jnt)
            # set locator local scale to match guide (applied on the locator transform and shape)
            try:
                shape = loc.getShape()
                if shape and hasattr(shape, "localScale"):
                    shape.localScale.set(pg_scale)
            except Exception:
                pass

            pm.parent(loc_grp, follow_grp)

            pm.parentConstraint(loc, jnt, mo=True)
            pm.scaleConstraint(loc, jnt)

        om2.MGlobal.displayInfo("Jaw build complete.")