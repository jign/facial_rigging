from abc import ABC, abstractmethod
import pymel.core as pm
from typing import Optional
from FaceJointGuides.core.names import *


class Component(ABC):
    def __init__(self):
        self._name: Optional[str] = None
        self._description: Optional[str] = None

    @staticmethod
    def get_top_grp(guide: pm.PyNode) -> pm.PyNode:
        if len(guide.listRelatives(p=1)) == 0:
            return guide
        return Component.get_top_grp(guide.listRelatives(p=1)[0])
    
    @staticmethod
    def _get_bucket_root_under_facial_guides(guide: pm.PyNode) -> Optional[pm.PyNode]:
        """
        If `guide` is somewhere under `FACIAL_GUIDES_GRP_NAME/<bucket>/...`,
        return the <bucket> transform PyNode.
        """
        node = guide
        while True:
            parents = node.listRelatives(p=True) or []
            if not parents:
                return None
            parent = parents[0]
            if parent.nodeName() == FACIAL_GUIDES_GRP_NAME:
                return node
            node = parent

    @staticmethod
    def get_bucket_name(guide: pm.PyNode) -> Optional[str]:
        """
        Returns bucket name like 'head' from:
          facial_guide_grp/head/l_brows_inner_guide
        """
        bucket_root = Component._get_bucket_root_under_facial_guides(guide)
        return bucket_root.nodeName() if bucket_root is not None else None

    @staticmethod
    def _ensure_child_group(parent: pm.PyNode, child_name: str) -> pm.PyNode:
        """
        Ensure an empty transform named `child_name` exists parented under `parent`.
        Matches by *child nodeName*, not global scene uniqueness.
        """
        children = parent.listRelatives(c=True, type="transform") or []
        for ch in children:
            if ch.nodeName() == child_name:
                return ch
        grp = pm.group(em=True, n=child_name)
        pm.parent(grp, parent)
        return grp

    @staticmethod
    def get_intermediate_jnts_grp(guide: pm.PyNode) -> pm.PyNode:
        """
        Returns:
          - jnts_grp/<bucket>_intermediate_grp if bucket exists
          - otherwise jnts_grp
        """
        jnts_top = pm.PyNode(JNTS_GRP_NAME)
        bucket = Component.get_bucket_name(guide)
        if not bucket:
            return jnts_top
        return Component._ensure_child_group(jnts_top, f"{bucket}_intermediate_grp")

    @staticmethod
    def get_intermediate_rig_grp(guide: pm.PyNode) -> pm.PyNode:
        """
        Returns:
          - rig_grp/<bucket>_rig_grp if bucket exists
          - otherwise rig_grp
        """
        rig_top = pm.PyNode(RIG_GRP_NAME)
        bucket = Component.get_bucket_name(guide)
        if not bucket:
            return rig_top
        return Component._ensure_child_group(rig_top, f"{bucket}_rig_grp")

    @staticmethod
    def build(guide: pm.PyNode):
        pass

    @abstractmethod
    def draw(self) -> pm.PyNode:
        pass

    def add_global_attrs(self, root_ctrl: Optional[pm.PyNode]):
        if root_ctrl is None or self._name is None:
            return

        root_ctrl.addAttr('comptype', nn='Component Type', dt='string')
        root_ctrl.comptype.set(self.name)

    @property
    def name(self) -> str:
        if self._name is None:
            return ""
        return self._name

    @property
    def description(self) -> str:
        if self._description is None:
            return ""
        return self._description
