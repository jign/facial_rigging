from FaceJointGuides.core.component import Component
import skylib.core.icon3d as i3d
import pymel.core as pm
import maya.cmds as cmds
import pymel.core.datatypes as dt
from typing import Optional
from FaceJointGuides.core.names import *


class PointControlComponent(Component):
    def __init__(self, instance_name: Optional[str] = None, loc: Optional[dt.Vector] = None):
        super().__init__()
        self._name = "point_control"
        self._instance_name: Optional[str] = instance_name
        self._draw_location: Optional[dt.Vector] = loc

    def draw(self) -> pm.PyNode:
        instance_name = self._instance_name if self._instance_name is not None else 'point_guide'
        guide_comp = i3d.make_crossball(1, instance_name, [1.0, 1.0, 0.0])
        self.add_global_attrs(guide_comp)
        if self._draw_location is not None:
            guide_comp.translate.set(self._draw_location)
        return guide_comp

    @staticmethod
    def build(guide: pm.PyNode):
        target_jnts_parent = Component.get_intermediate_jnts_grp(guide)
        target_rig_parent = Component.get_intermediate_rig_grp(guide)

        location = guide.getTranslation(space='world')

        # jnt_name = guide.getName().replace('guide', 'anim')
        jnt_name = f"{guide.getName()}_jnt_anim"
        # 1. create a joint
        jnt = pm.joint(target_jnts_parent, n=jnt_name, p=location)
        # reflect guide scale on the joint radius (use uniform average of sx,sy,sz)
        try:
            sx = guide.sx.get()
            sy = guide.sy.get()
            sz = guide.sz.get()
            uniform_scale = float((sx + sy + sz) / 3.0)
        except Exception:
            uniform_scale = 1.0
        try:
            jnt.radius.set(uniform_scale)
        except Exception:
            pass
        # 2. locator used by the animator
        loc_name = jnt.getName().replace('anim', 'ctrl')
        loc = pm.spaceLocator(n=loc_name)

        try:
            shape = loc.getShape()
            if shape is not None and hasattr(shape, 'localScale'):
                shape.localScale.set([uniform_scale, uniform_scale, uniform_scale])
        except Exception:
            pass
        # 3. group as a transform reference frame
        group = pm.group(loc, n=f'{loc_name}_grp')
        pt_cons = pm.pointConstraint(jnt, group)
        pm.delete(pt_cons)
        orient_cons = pm.orientConstraint(jnt, group)
        pm.delete(orient_cons)
        pm.makeIdentity(group, a=1, t=1, r=1)
        pm.parent(group, target_rig_parent)
        # 4. constrain the joint to the locator
        pm.parentConstraint(loc, jnt, mo=1)
        pm.scaleConstraint(loc, jnt)

