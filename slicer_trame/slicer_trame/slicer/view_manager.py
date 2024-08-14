from typing import Any

from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic


class ViewManager:
    """
    Class responsible for creating views given view descriptions and factories.
    Can create views
    """

    def __init__(self, scene: vtkMRMLScene, application_logic: vtkMRMLApplicationLogic):
        self.scene = scene
        self.app_logic = application_logic

    def register_factory(self, view_factory):
        """
        Allows to register a factory for given view type.
        """
        pass

    def get_view(self, view_id) -> Any:
        """
        Get view associated with ID
        """
        pass

    def create_view(self, view_id, view_type) -> Any:
        """
        Uses the best registered factory to create the view with given id / type.
        Overwrites view stored if it exists.
        Returns created view.

        If no factory can create view, raises exception.
        """
        pass

    def is_view_created(self, view_id) -> bool:
        """
        Returns true if view id is created, false otherwise.
        """
        pass
