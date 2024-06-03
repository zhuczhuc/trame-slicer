from typing import Optional, List

from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLViewNode, vtkMRMLAbstractViewNode
from vtkmodules.vtkMRMLDisplayableManager import vtkMRMLDisplayableManagerGroup
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer, vtkRenderWindowInteractor, vtkInteractorStyle


class AbstractView:
    """
    Simple container class for a VTK Render Window, Renderers and VTK MRML Displayable Manager Group
    """

    def __init__(self):
        self._renderer = vtkRenderer()
        self._render_window = vtkRenderWindow()
        self._render_window.SetMultiSamples(0)
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

    def renderer(self) -> vtkRenderer:
        return self.first_renderer()

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

    def reset_camera(self):
        for renderer in self._render_window.GetRenderers():
            renderer.ResetCamera()
