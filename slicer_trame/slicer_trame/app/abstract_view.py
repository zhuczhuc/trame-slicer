import asyncio
from typing import Optional, List

from trame_server.utils import asynchronous
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLViewNode, vtkMRMLAbstractViewNode
from vtkmodules.vtkMRMLDisplayableManager import vtkMRMLDisplayableManagerGroup
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkRenderer, vtkRenderWindowInteractor, vtkInteractorStyle


class ScheduledRenderStrategy:
    """
    Abstract class for handling scheduled rendering.
    Rendering update is triggered by Slicer's display managers.
    In asyncio context, the update can be managed using asyncio Tasks.
    In specific event loops, such as Qt, the rendering can be done using QTimer.
    """

    def __init__(self):
        self.abstract_view: Optional[AbstractView] = None

    def schedule_render(self):
        pass

    def did_render(self):
        pass

    def set_abstract_view(self, abstract_view: "AbstractView"):
        self.abstract_view = abstract_view


class NoScheduleRendering(ScheduledRenderStrategy):
    pass


class DirectRendering(ScheduledRenderStrategy):
    def schedule_render(self):
        if self.abstract_view:
            self.abstract_view.render()


class AsyncIORendering(ScheduledRenderStrategy):
    def __init__(self, schedule_render_fps: float = 30.):
        super().__init__()
        self.request_render_task: Optional[asyncio.Task] = None
        self.schedule_render_fps = schedule_render_fps

    def schedule_render(self):
        if self.request_render_task is None:
            self.request_render_task = asynchronous.create_task(self._async_render())
            self.request_render_task.add_done_callback(self.cleanup_render_task)

    async def _async_render(self):
        await asyncio.sleep(1. / self.schedule_render_fps)
        if self.abstract_view:
            self.abstract_view.render()

    def did_render(self):
        if self.request_render_task is not None:
            self.request_render_task.cancel()
            self.request_render_task = None

    def cleanup_render_task(self, *_):
        self.request_render_task = None


class AbstractView:
    """
    Simple container class for a VTK Render Window, Renderers and VTK MRML Displayable Manager Group
    """

    def __init__(self, scheduled_render_strategy: Optional[ScheduledRenderStrategy] = None, *args, **kwargs):
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

        self._scheduled_render = scheduled_render_strategy or DirectRendering()
        self._scheduled_render.set_abstract_view(self)

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
        self._scheduled_render.schedule_render()

    def render(self) -> None:
        self._render_window.Render()
        self._scheduled_render.did_render()

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
