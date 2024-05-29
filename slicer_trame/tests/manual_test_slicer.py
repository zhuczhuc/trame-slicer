from slicer import *
from typing import Optional, List
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer, vtkRenderWindowInteractor, vtkInteractorStyle

class SlicerApp:
    def __init__(self):
        import slicer
        self.app_logic = slicer.app.applicationLogic()
        self.scene = slicer.mrmlScene

class AbstractView:
    """
    Simple container class for a VTK Render Window, Renderers and VTK MRML Displayable Manager Group
    """

    def __init__(self):
        self._renderer = vtkRenderer()
        self._render_window = vtkRenderWindow()
        self._render_window.AddRenderer(self._renderer)

        self._render_window_interactor = vtkRenderWindowInteractor()
        self._render_window_interactor.SetRenderWindow(self._render_window)

        self.displayable_manager_group = vtkMRMLDisplayableManagerGroup()
        self.displayable_manager_group.SetRenderer(self._renderer)

        self.mrml_scene: Optional[vtkMRMLScene] = None
        self.mrml_view_node: Optional[vtkMRMLAbstractViewNode] = None

    def add_renderer(self, renderer: vtkRenderer) -> None:
        self._render_window.AddRenderer(renderer)

    def renderers(self) -> List[vtkRenderer]:
        return list(self._render_window.GetRenderers())

    def first_renderer(self) -> vtkRenderer:
        return self._renderer

    def render(self) -> None:
        self._render_window.Render()

    def render_window(self) -> vtkRenderWindow:
        return self._render_window

    def set_interactor(self, interactor: vtkRenderWindowInteractor) -> None:
        self.render_window().SetInteractor(interactor)

    def interactor(self) -> Optional[vtkRenderWindowInteractor]:
        return self.render_window().GetInteractor()

    def interactor_style(self) -> Optional[vtkInteractorStyle]:
        return self.interactor().GetInteractorStyle() if self.interactor() else None

    def set_interactor_style(self, style: Optional[vtkInteractorStyle]) -> None:
        if self.interactor():
            self.interactor().SetInteractorStyle(style)

    def set_mrml_view_node(self, node: vtkMRMLViewNode) -> None:
        if self.mrml_view_node == node:
            return

        self.mrml_view_node = node
        self.displayable_manager_group.SetMRMLDisplayableNode(node)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        if self.mrml_scene == scene:
            return

        self.mrml_scene = scene
        if self.mrml_view_node and self.mrml_view_node.GetScene() != scene:
            self.mrml_view_node = None

class SliceView(AbstractView):
    def __init__(self, app: SlicerApp, name: str):
        super().__init__()

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

        self.name = name
        self.logic = vtkMRMLSliceLogic()
        self.logic.SetMRMLApplicationLogic(app.app_logic)
        self.set_mrml_scene(app.scene)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        super().set_mrml_scene(scene)
        self.logic.SetMRMLScene(scene)
        if self.mrml_view_node is None:
            self.set_mrml_view_node(self.logic.AddSliceNode(self.name))

import SampleData
node = volumeNode = SampleData.SampleDataLogic().downloadMRHead()
node.CreateDefaultDisplayNodes()

a_slicer_app = SlicerApp()
a_slice_view = SliceView(a_slicer_app, "MYOWN")
a_slice_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(node.GetID())
a_slice_view.mrml_view_node.SetOrientation("Coronal")
# a_slice_view.logic.FitSliceToAll()
a_slice_view.logic.SetSliceOffset(0)
a_slice_view.render()
a_slice_view.interactor().Start()
