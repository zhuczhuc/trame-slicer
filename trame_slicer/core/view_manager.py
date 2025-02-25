from itertools import chain
from typing import TypeVar

from slicer import vtkMRMLApplicationLogic, vtkMRMLScene

from trame_slicer.views import (
    AbstractView,
    AbstractViewChild,
    IViewFactory,
    SliceView,
    ThreeDView,
    ViewLayoutDefinition,
)

T = TypeVar("T")


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

    def register_factory(self, view_factory: IViewFactory) -> None:
        """
        Allows to register a factory for given view type.
        """
        self._factories.append(view_factory)

    def get_view(self, view_id: str) -> AbstractViewChild | None:
        """
        Get view associated with ID
        """
        for factory in self._factories:
            if factory.has_view(view_id):
                return factory.get_view(view_id)
        return None

    def remove_view(self, view_id: str) -> bool:
        for factory in self._factories:
            if factory.has_view(view_id):
                return factory.remove_view(view_id)
        return False

    def create_view(self, view: ViewLayoutDefinition) -> AbstractViewChild | None:
        """
        Uses the best registered factory to create the view with given id / type.
        Overwrites view stored if it exists.
        Returns created view.
        """
        view_id = view.singleton_tag
        if self.is_view_created(view_id):
            return self.get_view(view_id)

        for factory in self._factories:
            if factory.can_create_view(view):
                return factory.create_view(view, self._scene, self._app_logic)
        return None

    def is_view_created(self, view_id: str) -> bool:
        """
        Returns true if view id is created, false otherwise.
        """
        return any(factory.has_view(view_id) for factory in self._factories)

    def get_views(self, view_group: int | None = None) -> list[AbstractView]:
        views = list(chain(*[factory.get_views() for factory in self._factories]))
        return [
            view
            for view in views
            if (view_group is None or view.get_view_group() == view_group)
        ]

    def get_slice_views(self, view_group: int | None = None) -> list[SliceView]:
        return self._get_view_type(SliceView, view_group)

    def get_threed_views(self, view_group: int | None = None) -> list[ThreeDView]:
        return self._get_view_type(ThreeDView, view_group)

    def _get_view_type(
        self,
        view_type: type[T],
        view_group: int | None = None,
    ) -> list[T]:
        return [
            view for view in self.get_views(view_group) if isinstance(view, view_type)
        ]
