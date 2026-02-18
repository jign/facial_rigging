import pymel.core as pm


def add_control_to_jnt(jnt: pm.PyNode):
    # 2. locator used by the animator
    loc_name = jnt.getName().replace('anim', 'ctrl')
    loc = pm.spaceLocator(n=loc_name)
    # 3. group as a transform reference frame
    group = pm.group(loc, n=f'{loc_name}_grp')
    pt_cons = pm.pointConstraint(jnt, group)
    pm.delete(pt_cons)
    orient_cons = pm.orientConstraint(jnt, group)
    pm.delete(orient_cons)
    pm.makeIdentity(group, a=1, t=1, r=1)
    # 4. constrain the joint to the locator
    pm.parentConstraint(loc, jnt, mo=1)
    pm.scaleConstraint(loc, jnt)


# TODO fix rotation pivot
def add_control_to_joint_with_offset(jnt: pm.PyNode, offset_obj: pm.PyNode):
    # 2. locator used by the animator
    loc_name = jnt.getName().replace('anim', 'ctrl')
    loc = pm.spaceLocator(n=loc_name)
    # 3. group as a transform reference frame
    group = pm.group(loc, n=f'{loc_name}_grp')
    pt_cons = pm.pointConstraint(offset_obj, group)
    pm.delete(pt_cons)
    orient_cons = pm.orientConstraint(offset_obj, group)
    pm.delete(orient_cons)
    pm.makeIdentity(group, a=1, t=1, r=1)
    # 4. constrain the joint to the locator
    pm.parentConstraint(loc, jnt, mo=1)
    pm.scaleConstraint(loc, jnt)
