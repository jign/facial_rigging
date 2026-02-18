from abc import ABC

from FaceJointGuides.core.component import Component
import pymel.core as pm


class NeckComponent(Component, ABC):
    def __init__(self):
        super().__init__()
        self._name = 'neck'

    def draw(self):
        pass

    @staticmethod
    def build(guide: pm.PyNode):
        pass
