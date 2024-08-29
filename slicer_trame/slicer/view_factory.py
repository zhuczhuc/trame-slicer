from abc import ABC, abstractmethod
from typing import Optional, TypeVar

from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from .abstract_view import AbstractView, AbstractViewChild
from .view_layout_definition import ViewLayoutDefinition

V = TypeVar("V")


class IViewFactory(ABC):
    """
    Interface for view factories.
    """

    def __init__(self):
        self._views: dict[str, V] = dict()

    @abstractmethod
    def can_create_view(self, view: ViewLayoutDefinition) -> bool:
        pass

    def create_view(
        self,
        view: ViewLayoutDefinition,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ) -> AbstractView:
        self._views[view.singleton_tag] = self._create_view(view, scene, app_logic)
        return self.get_view(view.singleton_tag)

    def remove_view(self, view_id: str) -> bool:
        if not self.has_view(view_id):
            return False

        del self._views[view_id]
        return True

    @abstractmethod
    def _create_view(
        self,
        view: ViewLayoutDefinition,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ) -> V:
        pass

    def get_view(self, view_id: str) -> Optional[AbstractViewChild]:
        view = self.get_factory_view(view_id)
        if view is None:
            return None
        return self._get_slicer_view(view)

    def get_factory_view(self, view_id) -> Optional[V]:
        if not self.has_view(view_id):
            return None
        return self._views[view_id]

    def get_views(self) -> list[AbstractViewChild]:
        return [self._get_slicer_view(view) for view in self._views.values()]

    def has_view(self, view_id: str) -> bool:
        return view_id in self._views

    @abstractmethod
    def _get_slicer_view(self, view: V) -> AbstractViewChild:
        pass
