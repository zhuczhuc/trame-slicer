from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLDisplayableManager import (
    vtkMRMLCameraDisplayableManager, vtkMRMLViewDisplayableManager, vtkMRMLModelDisplayableManager,
    vtkMRMLThreeDReformatDisplayableManager, vtkMRMLCrosshairDisplayableManager3D,
    vtkMRMLOrientationMarkerDisplayableManager, vtkMRMLRulerDisplayableManager, vtkMRMLThreeDViewInteractorStyle
)
from vtkmodules.vtkMRMLLogic import vtkMRMLViewLogic

from .abstract_view import AbstractView
from .slicer_app import SlicerApp


class ThreeDView(AbstractView):
    def __init__(self, app: SlicerApp, name: str):
        super().__init__()

        managers = [
            vtkMRMLCameraDisplayableManager,
            vtkMRMLViewDisplayableManager,
            vtkMRMLModelDisplayableManager,
            vtkMRMLThreeDReformatDisplayableManager,
            vtkMRMLCrosshairDisplayableManager3D,
            vtkMRMLOrientationMarkerDisplayableManager,
            vtkMRMLRulerDisplayableManager,
        ]

        for manager in managers:
            manager = manager()
            manager.SetMRMLApplicationLogic(app.app_logic)
            self.displayable_manager_group.AddDisplayableManager(manager)

        self.interactor_observer = vtkMRMLThreeDViewInteractorStyle()
        self.interactor_observer.SetDisplayableManagers(self.displayable_manager_group)
        self.displayable_manager_group.GetInteractor().Initialize()

        self.name = name
        self.logic = vtkMRMLViewLogic()
        self.logic.SetMRMLApplicationLogic(app.app_logic)
        self.set_mrml_scene(app.scene)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        super().set_mrml_scene(scene)
        self.logic.SetMRMLScene(scene)
        if self.mrml_view_node is None:
            self.set_mrml_view_node(self.logic.AddViewNode(self.name))
