from typing import Any
from weakref import WeakValueDictionary

from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from slicer_trame.components.layout_grid import SlicerView
from slicer_trame.slicer.view_factory import IViewFactory


class ViewManager:
    """
    Class responsible for creating views given view descriptions and factories.
    Create views with the first factory available which can create view spec.
    Provides access to created views but doesn't hold strong ownership of the views.
    """

    def __init__(self, scene: vtkMRMLScene, application_logic: vtkMRMLApplicationLogic):
        self._scene = scene
        self._app_logic = application_logic
        self._factories: list[IViewFactory] = []
        self._views = WeakValueDictionary()

    def register_factory(self, view_factory: IViewFactory) -> None:
        """
        Allows to register a factory for given view type.
        """
        self._factories.append(view_factory)

    def get_view(self, view_id: str) -> Any:
        """
        Get view associated with ID
        """
        return self._views.get(view_id)

    def create_view(self, view: SlicerView) -> Any:
        """
        Uses the best registered factory to create the view with given id / type.
        Overwrites view stored if it exists.
        Returns created view.

        If no factory can create view, raises exception.
        """
        view_id = view.singleton_tag
        if self.is_view_created(view_id):
            return self.get_view(view_id)

        for factory in self._factories:
            if factory.can_create_view(view):
                created_view = factory.create_view(view, self._scene, self._app_logic)
                self._views[view_id] = created_view
                return created_view

    def is_view_created(self, view_id: str) -> bool:
        """
        Returns true if view id is created, false otherwise.
        """
        return view_id in self._views
