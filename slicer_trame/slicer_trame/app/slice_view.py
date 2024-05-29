from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLDisplayableManager import (
    vtkMRMLVolumeGlyphSliceDisplayableManager, vtkMRMLModelSliceDisplayableManager, vtkMRMLCrosshairDisplayableManager,
    vtkMRMLOrientationMarkerDisplayableManager, vtkMRMLRulerDisplayableManager, vtkMRMLScalarBarDisplayableManager,
    vtkMRMLSliceViewInteractorStyle, vtkMRMLLightBoxRendererManagerProxy
)
from vtkmodules.vtkMRMLLogic import vtkMRMLSliceLogic
from vtkmodules.vtkRenderingCore import vtkActor2D, vtkImageMapper, vtkImageActor

from .abstract_view import AbstractView
from .slicer_app import SlicerApp


class SliceRendererManager(vtkMRMLLightBoxRendererManagerProxy):
    """
    In 3D Slicer the image actor is handled by CTK vtkLightBoxRendererManager currently not wrapped in SlicerLib
    This render manager implements a one image actor / mapper for the renderining without lightbox features.

    It combines the vtkLightBoxRendererManager and vtkMRMLLightBoxRendererManagerProxy features.

    :see: https://github.com/commontk/CTK/blob/master/Libs/Visualization/VTK/Core/vtkLightBoxRendererManager.cpp
    :see: D:\W\Slicer\Libs\MRML\Widgets\qMRMLSliceControllerWidget.cxx
    """

    def __init__(self, view: "SliceView"):
        super().__init__()
        self.view = view

        # self.image_mapper = vtkImageMapper()
        # self.image_actor = vtkActor2D()
        self.image_actor = vtkImageActor()
        # self.image_actor.SetMapper(self.image_mapper)
        # self.image_actor.GetProperty().SetDisplayLocationToBackground()

    def GetRenderer(self, _):
        return self.view.first_renderer()

    def SetImageDataConnection(self, imageDataConnection):
        self.image_actor.GetMapper().SetInputConnection(imageDataConnection)
        self.add_slice_actor_to_renderer_if_needed()
        # self.image_actor.SetVisibility(bool(imageDataConnection))
        # self.image_actor.SetForceOpaque(True)

    def add_slice_actor_to_renderer_if_needed(self):
        renderer = self.GetRenderer(0)
        if renderer.HasViewProp(self.image_actor):
            return

        renderer.AddViewProp(self.image_actor)


class SliceView(AbstractView):
    def __init__(self, app: SlicerApp, name: str):
        super().__init__()

        # Add Render manager
        self.render_manager = SliceRendererManager(self)
        self.first_renderer().GetActiveCamera().ParallelProjectionOn()

        self.image_data_connection = None

        managers = [
            vtkMRMLVolumeGlyphSliceDisplayableManager,
            vtkMRMLModelSliceDisplayableManager,
            vtkMRMLCrosshairDisplayableManager,
            vtkMRMLOrientationMarkerDisplayableManager,
            vtkMRMLRulerDisplayableManager,
            vtkMRMLScalarBarDisplayableManager,
        ]

        for manager in managers:
            manager = manager()
            manager.SetMRMLApplicationLogic(app.app_logic)
            self.displayable_manager_group.AddDisplayableManager(manager)

        self.interactor_observer = vtkMRMLSliceViewInteractorStyle()
        self.interactor_observer.SetDisplayableManagers(self.displayable_manager_group)
        self.displayable_manager_group.GetInteractor().Initialize()
        self.displayable_manager_group.SetLightBoxRendererManagerProxy(self.render_manager)

        self.name = name

        # Create slice logic
        self.logic = vtkMRMLSliceLogic()
        self.logic.SetMRMLApplicationLogic(app.app_logic)
        self.logic.AddObserver(vtkCommand.ModifiedEvent, self.on_slice_logic_modified_event)
        self.interactor_observer.SetSliceLogic(self.logic)

        # Connect to scene
        self.set_mrml_scene(app.scene)

    def setup_rendering(self):
        self.render_window().SetAlphaBitPlanes(1)
        self.render_window().SetNumberOfLayers(2)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        super().set_mrml_scene(scene)
        self.logic.SetMRMLScene(scene)
        if self.mrml_view_node is None:
            self.set_mrml_view_node(self.logic.AddSliceNode(self.name))

    def on_slice_logic_modified_event(self, *_):
        self.update_image_data_connection()
        self.update_offset_slider()

    def update_image_data_connection(self):
        image_data_connection = self.logic.GetImageDataConnection()
        if self.image_data_connection == image_data_connection:
            return

        self.image_data_connection = image_data_connection
        self.render_manager.SetImageDataConnection(self.image_data_connection)

    def update_offset_slider(self):
        pass
