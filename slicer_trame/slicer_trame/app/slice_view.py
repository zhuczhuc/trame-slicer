import vtk
from vtkmodules.vtkCommonCore import vtkCommand, vtkCallbackCommand
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleUser
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLDisplayableManager import (
    vtkMRMLVolumeGlyphSliceDisplayableManager, vtkMRMLModelSliceDisplayableManager, vtkMRMLCrosshairDisplayableManager,
    vtkMRMLOrientationMarkerDisplayableManager, vtkMRMLRulerDisplayableManager, vtkMRMLScalarBarDisplayableManager,
    vtkMRMLSliceViewInteractorStyle, vtkMRMLLightBoxRendererManagerProxy
)
from vtkmodules.vtkMRMLLogic import vtkMRMLSliceLogic
from vtkmodules.vtkRenderingCore import vtkActor2D, vtkImageMapper, vtkRenderer

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

        # Create Slice image mapper and set its window / level fix to 8bit
        # The window / level setting based on the input vtkImageData is handled by the vtkVolumeDisplayNode
        # The generated image data is RGBA between 0/255
        self.image_mapper = vtkImageMapper()
        self.image_mapper.SetColorWindow(255)
        self.image_mapper.SetColorLevel(127.5)

        self.image_actor = vtkActor2D()
        self.image_actor.SetMapper(self.image_mapper)
        self.image_actor.GetProperty().SetDisplayLocationToBackground()

    def GetRenderer(self, _):
        return self.view.first_renderer()

    def SetImageDataConnection(self, imageDataConnection):
        self.image_actor.GetMapper().SetInputConnection(imageDataConnection)
        self.add_slice_actor_to_renderer_if_needed()
        self.image_actor.SetVisibility(bool(imageDataConnection))

    def add_slice_actor_to_renderer_if_needed(self):
        renderer = self.GetRenderer(0)
        if renderer.HasViewProp(self.image_actor):
            return

        renderer.AddViewProp(self.image_actor)


class SliceView(AbstractView):
    def __init__(self, app: SlicerApp, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.first_renderer().GetActiveCamera().ParallelProjectionOn()

        self.overlay_renderer = vtkRenderer()
        self.overlay_renderer.GetActiveCamera().ParallelProjectionOn()
        self.overlay_renderer.SetLayer(1)
        self.render_window().SetNumberOfLayers(2)
        self.render_window().AddRenderer(self.overlay_renderer)
        self.render_window().SetAlphaBitPlanes(1)
        self.render_window().AddObserver(vtkCommand.WindowResizeEvent, self.update_slice_size)

        # Add Render manager
        self.render_manager = SliceRendererManager(self)

        self.image_data_connection = None

        managers = [
            vtkMRMLCrosshairDisplayableManager,
            vtkMRMLVolumeGlyphSliceDisplayableManager,
            vtkMRMLModelSliceDisplayableManager,
            vtkMRMLOrientationMarkerDisplayableManager,
            vtkMRMLRulerDisplayableManager,
            vtkMRMLScalarBarDisplayableManager,
        ]

        for manager in managers:
            manager = manager()
            manager.SetMRMLApplicationLogic(app.app_logic)
            self.displayable_manager_group.AddDisplayableManager(manager)

        self.displayable_manager_group.SetLightBoxRendererManagerProxy(self.render_manager)
        self.interactor_observer = vtkMRMLSliceViewInteractorStyle()
        self.name = name

        # Create slice logic
        self.logic = vtkMRMLSliceLogic()
        self.logic.SetMRMLApplicationLogic(app.app_logic)
        self.logic.AddObserver(vtkCommand.ModifiedEvent, self.on_slice_logic_modified_event)
        app.app_logic.GetSliceLogics().AddItem(self.logic)

        self.interactor_observer.SetSliceLogic(self.logic)
        self.interactor_observer.SetDisplayableManagers(self.displayable_manager_group)

        # Connect to scene
        self.set_mrml_scene(app.scene)
        self.interactor().SetInteractorStyle(vtkInteractorStyleUser())
        self.interactor_observer.SetInteractor(self.interactor())

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        super().set_mrml_scene(scene)
        self.logic.SetMRMLScene(scene)
        if self.mrml_view_node is None:
            self.set_mrml_view_node(self.logic.AddSliceNode(self.name))

    def on_slice_logic_modified_event(self, *_):
        self.update_image_data_connection()

    def update_image_data_connection(self):
        image_data_connection = self.logic.GetImageDataConnection()
        if self.image_data_connection == image_data_connection:
            return

        self.image_data_connection = image_data_connection
        self.render_manager.SetImageDataConnection(self.image_data_connection)

    def update_slice_size(self, *_):
        self.logic.ResizeSliceNode(*self.render_window().GetSize())
