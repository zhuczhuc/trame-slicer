from typing import Optional, List

from vtkmodules.vtkCommonCore import vtkCommand
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
        self.displayable_manager_group.AddObserver(vtkCommand.UpdateEvent, self.schedule_render)
        self.mrml_scene: Optional[vtkMRMLScene] = None
        self.mrml_view_node: Optional[vtkMRMLAbstractViewNode] = None

    def finalize(self):
        self.render_window().ShowWindowOff()
        self.render_window().Finalize()

    def add_renderer(self, renderer: vtkRenderer) -> None:
        self._render_window.AddRenderer(renderer)

    def renderers(self) -> List[vtkRenderer]:
        return list(self._render_window.GetRenderers())

    def first_renderer(self) -> vtkRenderer:
        return self._renderer

    def renderer(self) -> vtkRenderer:
        return self.first_renderer()

    def schedule_render(self, *_) -> None:
        self.render()

    def render(self) -> None:
        self._render_window.Render()

    def render_window(self) -> vtkRenderWindow:
        return self._render_window

    def interactor(self) -> Optional[vtkRenderWindowInteractor]:
        return self.render_window().GetInteractor()

    def interactor_style(self) -> Optional[vtkInteractorStyle]:
        return self.interactor().GetInteractorStyle() if self.interactor() else None

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

    def print_event(self, *args):
        print(args)

    def add_print_observers(self):
        self.interactor().AddObserver(vtkCommand.MouseMoveEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.RightButtonDoubleClickEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.RightButtonPressEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.RightButtonReleaseEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.MiddleButtonDoubleClickEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.MiddleButtonPressEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.MiddleButtonReleaseEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.LeftButtonDoubleClickEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.LeftButtonPressEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.LeftButtonReleaseEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.EnterEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.LeaveEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.MouseWheelForwardEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.MouseWheelBackwardEvent, self.print_event)

        # Touch gesture
        self.interactor().AddObserver(vtkCommand.StartPinchEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.PinchEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.EndPinchEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.StartRotateEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.RotateEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.EndRotateEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.StartPanEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.PanEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.EndPanEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.TapEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.LongTapEvent, self.print_event)

        # Keyboard
        self.interactor().AddObserver(vtkCommand.KeyPressEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.KeyReleaseEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.CharEvent, self.print_event)

        # 3D event bindings
        self.interactor().AddObserver(vtkCommand.Button3DEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.Move3DEvent, self.print_event)

        self.interactor().AddObserver(vtkCommand.ExposeEvent, self.print_event)
        self.interactor().AddObserver(vtkCommand.ConfigureEvent, self.print_event)
