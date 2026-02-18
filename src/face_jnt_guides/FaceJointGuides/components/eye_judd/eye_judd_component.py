from FaceJointGuides.core.component import Component
from FaceJointGuides.components.point_control.point_control_component import PointControlComponent
import FaceJointGuides.core.control as ctrl
import skylib.core.icon3d as i3d
import pymel.core.datatypes as dt
import pymel.core as pm
from typing import Dict
from FaceJointGuides.core.names import *


class EyeJuddComponent(Component):
    def __init__(self):
        super().__init__()
        self._name = "eye_judd"
        self.num_controls: int = 6
        self.ctrls: Dict[str, dt.Vector] = self.__init_ctrl_dict()
        self.side: str = 'l'  # 'l' or 'r'

    def _prompt_side_toggle(self) -> str:
        """Popup to request side toggle; returns 'l' or 'r'."""
        res = pm.confirmDialog(
            title='Eye Side',
            message='Select side for this eye guide:',
            button=['L', 'R', 'Cancel'],
            defaultButton='L',
            cancelButton='Cancel',
            dismissString='Cancel'
        )
        if res == 'R':
            return 'r'
        return 'l'

    def draw(self):
        self.side = self._prompt_side_toggle()
        core = i3d.make_crosscube(1, f'{self.side}_eye_nucleus_guide', [0.0, 0.0, 1.0])
        core_grp = pm.group(em=1, n=f'{self.side}_eye_grp')
        self.add_global_attrs(core_grp)
        ghostline_grp = pm.group(em=1, n=f'{self.side}_eye_ghost_grp')
        ctrls_grp = pm.group(em=1, n=f'{self.side}_eye_ctrls_grp')
        pm.parent(core, core_grp)
        pm.parent(ctrls_grp, core_grp)
        pm.parent(ghostline_grp, core_grp)

        for ctrl_name, ctrl_pos in self.ctrls.items():
            eye_ctrl = i3d.make_crossball(1, f'{self.side}_{ctrl_name}_guide', [1.0, 1.0, 0.0])
            eye_ctrl.translate.set(ctrl_pos)
            pm.parent(eye_ctrl, ctrls_grp)
            ghostline = i3d.make_ghostline(f'{self.side}_{ctrl_name}_ghostline', [core, eye_ctrl])
            pm.parent(ghostline, ghostline_grp)

    @staticmethod
    def build(guide: pm.PyNode):
        side = guide.getName().split('_')[0]

        # Use bucket-based intermediate parents (facial_guide_grp/<bucket>/...).
        target_rig_parent = Component.get_intermediate_rig_grp(guide)
        target_jnts_parent = Component.get_intermediate_jnts_grp(guide)

        # Keep per-eye organization, but parent it under the bucket rig group.
        subgrp = pm.group(em=1, n=f'{side}_eye_rig_grp')
        pm.parent(subgrp, target_rig_parent)
        target_grp = subgrp

        nucleus_guide_name = f"{side}_eye_nucleus_guide"
        nucleus_guide = pm.PyNode(nucleus_guide_name)

        # IMPORTANT: use worldspace positions (don’t mix local + world)
        nucleus_loc = dt.Vector(*pm.xform(nucleus_guide, q=True, ws=True, t=True))

        # 0. Assume the guide is the eye_grp, improve later
        guide_grp_name = f'{side}_eye_ctrls_grp'
        guide_grp = pm.PyNode(guide_grp_name)

        # 1. Find all children of the guides group, except for the canthus joints
        for guide_name in [guide for guide in guide_grp.listRelatives() if 'canthus' not in guide.getName()]:
            guide_node = pm.PyNode(guide_name)
            # Worldspace guide location
            guide_loc = dt.Vector(*pm.xform(guide_node, q=True, ws=True, t=True))
            # read guide local scale (object space)
            try:
                pg_scale = pm.xform(guide_node, q=True, s=True, ws=False)
            except Exception:
                pg_scale = [1.0, 1.0, 1.0]
            pg_scale_avg = sum(pg_scale) / 3.0

            # 2. For each, create an anim joint and move it to the location of the current guide
            # 3. create a joint and move it to the location of the nucleus, call it pivot_anim
            # Create joints in world, then parent (keeps world position)
            pm.select(clear=True)
            pivot_jnt = pm.joint(n=guide_name.replace('guide', 'jnt_pivot_anim'), p=nucleus_loc)
            pm.select(clear=True)
            anim_jnt = pm.joint(n=guide_name.replace('guide', 'jnt_anim'), p=guide_loc)

            pm.parent(anim_jnt, pivot_jnt)                 # keep world by default
            pm.parent(pivot_jnt, target_jnts_parent)       # keep world by default
            # set joint radiuses to match guide scale (use average as scalar)
            try:
                pivot_jnt.radius.set(pg_scale_avg)
            except Exception:
                try:
                    pm.setAttr(f"{pivot_jnt}.radius", pg_scale_avg)
                except Exception:
                    pass
            try:
                anim_jnt.radius.set(pg_scale_avg)
            except Exception:
                try:
                    pm.setAttr(f"{anim_jnt}.radius", pg_scale_avg)
                except Exception:
                    pass

            # 3. Parent each newly created joint to their parent (the anim to the pivot_anim)
            # pm.parent(anim_jnt, pivot_jnt)
            # TODO eventually do this? or make a sky eye component
            # ctrl.add_control_to_joint_with_offset(pivot_jnt, anim_jnt)
            # ctrl.add_control_to_jnt(pivot_jnt)

            # 2. locator used by the animator
            loc_name = pivot_jnt.getName().replace('anim', 'ctrl')
            loc = pm.spaceLocator(n=loc_name)

            # apply local scale to locator and its shape to match guide
            try:
                shape = loc.getShape()
                if shape and hasattr(shape, "localScale"):
                    shape.localScale.set(pg_scale)
            except Exception:
                pass

            # 3. group as a transform reference frame
            group = pm.group(loc, n=f'{loc_name}_grp')
            pt_cons = pm.pointConstraint(pivot_jnt, group)
            pm.delete(pt_cons)
            orient_cons = pm.orientConstraint(pivot_jnt, group)
            pm.delete(orient_cons)
            pm.makeIdentity(group, a=1, t=1, r=1)
            pm.parent(group, target_grp)
            # 4. constrain the joint to the locator
            pm.parentConstraint(loc, pivot_jnt, mo=1)
            pm.scaleConstraint(loc, pivot_jnt)

        for guide_name in [guide for guide in guide_grp.listRelatives() if 'canthus' in guide.getName()]:
            guide_node = pm.PyNode(guide_name)

            # Worldspace guide location
            guide_loc = dt.Vector(*pm.xform(guide_node, q=True, ws=True, t=True))

            # read guide local scale (object space)
            try:
                pg_scale = pm.xform(guide_node, q=True, s=True, ws=False)
            except Exception:
                pg_scale = [1.0, 1.0, 1.0]
            pg_scale_avg = sum(pg_scale) / 3.0

            # 2. For each, create an anim joint and move it to the location of the current guide
            # Create in world, then parent under target group (keeps world)
            pm.select(clear=True)
            anim_jnt = pm.joint(n=guide_name.replace('guide', 'jnt_anim'), p=guide_loc)
            pm.parent(anim_jnt, target_jnts_parent)
            
            # set joint radius to match guide scale
            try:
                anim_jnt.radius.set(pg_scale_avg)
            except Exception:
                try:
                    pm.setAttr(f"{anim_jnt}.radius", pg_scale_avg)
                except Exception:
                    pass

            # 2. locator used by the animator
            loc_name = anim_jnt.getName().replace('anim', 'ctrl')
            loc = pm.spaceLocator(n=loc_name)

            # apply local scale to locator and its shape to match guide
            try:
                shape = loc.getShape()
                if shape and hasattr(shape, "localScale"):
                    shape.localScale.set(pg_scale)
            except Exception:
                pass

            # 3. group as a transform reference frame
            group = pm.group(loc, n=f'{loc_name}_grp')
            pt_cons = pm.pointConstraint(anim_jnt, group)
            pm.delete(pt_cons)
            orient_cons = pm.orientConstraint(anim_jnt, group)
            pm.delete(orient_cons)
            pm.makeIdentity(group, a=1, t=1, r=1)
            pm.parent(group, target_grp)
            # 4. constrain the joint to the locator
            pm.parentConstraint(loc, anim_jnt, mo=1)
            pm.scaleConstraint(loc, anim_jnt)

    @staticmethod
    def __init_ctrl_dict() -> Dict[str, dt.Vector]:
        ctrls_dict = {
            'inner_canthus': dt.Vector(-3.5, 0, 2.5),
            'outer_canthus': dt.Vector(3.0, 0, 2.5),
            'upper_lid_1': dt.Vector(-2.5, 1.6, 2.5),
            'upper_lid_2': dt.Vector(0, 2.25, 2.5),
            'upper_lid_3': dt.Vector(2.5, 1.6, 2.5),
            'lower_lid_1': dt.Vector(-2.5, -1.6, 2.5),
            'lower_lid_2': dt.Vector(0, -2.25, 2.5),
            'lower_lid_3': dt.Vector(2.5, -1.6, 2.5),
        }

        return ctrls_dict
