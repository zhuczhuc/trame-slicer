import asyncio
import json
import time
from asyncio import Task
from typing import Optional

from trame.app import asynchronous
from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter, vtkWebApplication

from slicer_trame.components.web_application import WebApplication
from slicer_trame.slicer import AbstractView
from slicer_trame.slicer.render_scheduler import ScheduledRenderStrategy


class RcaViewAdapter:
    """
    Adapter for a Remote controlled area
    Based on implementation : https://github.com/Kitware/trame-rca/blob/master/examples/00_cone/app.py
    """

    def __init__(
        self,
        view: AbstractView,
        name: str,
        web_application: Optional[vtkWebApplication] = None,
        target_fps: float = 60.0,
        interactive_quality: int = 50,
    ):
        self._view = view
        self._view.set_scheduled_render(RcaRenderScheduler(self, target_fps=target_fps))
        self._window = view.render_window()
        self.area_name = name
        self.streamer = None
        self._prev_data_m_time = None
        self._interactive_quality = interactive_quality

        self._iren = self._window.GetInteractor()
        self._iren.EnableRenderOff()
        self._window.ShowWindowOff()
        self._web_application = web_application or WebApplication.get_singleton()

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # mime time
            codec="",  # video codec, not relevant here
            w=self._window.GetSize()[0],
            h=self._window.GetSize()[1],
            st=int(time.time_ns() / 1000000),
            key=("key"),  # jpegs are always keyframes
        )

    def invalidate_cache(self):
        self._web_application.InvalidateCache(self._window)

    def render_and_push(self, is_animating: bool, do_invalidate_cache: bool) -> bool:
        if do_invalidate_cache:
            self.invalidate_cache()

        data = self._web_application.StillRender(
            self._window, self._interactive_quality if is_animating else 100
        )
        if data.m_time == self._prev_data_m_time:
            return False

        self._prev_data_m_time = data.m_time
        self.push(memoryview(data), self._get_metadata())
        return True

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        # Resize to one pixel min to avoid rendering problems in VTK
        width = max(1, int(size.get("w", 300)))
        height = max(1, int(size.get("h", 300)))
        self._iren.UpdateSize(width, height)
        self.schedule_render()

    def schedule_render(self):
        self._view.schedule_render()

    def push(self, content, meta=None):
        if not self.streamer:
            return

        if content is None:
            return

        self.streamer.push_content(self.area_name, meta, content)

    def on_interaction(self, _, event):
        event_type = event["type"]
        if event_type in ["StartInteractionEvent", "EndInteractionEvent"]:
            return

        status = vtkRemoteInteractionAdapter.ProcessEvent(self._iren, json.dumps(event))
        if status:
            self.schedule_render()


class RcaRenderScheduler(ScheduledRenderStrategy):
    def __init__(self, rca_adapter: RcaViewAdapter, target_fps: float):
        super().__init__()
        self._adapter = rca_adapter
        self._animate_task: Optional[Task] = None
        self._cancel_animate_task: Optional[Task] = None
        self._do_animate = False
        self._target_fps = target_fps

    def schedule_render(self):
        if self._animate_task is None or not self._do_animate:
            self._do_animate = True
            self._animate_task = asynchronous.create_task(self._animate())

        if self._cancel_animate_task is not None:
            self._cancel_animate_task.cancel()
            self._cancel_animate_task = None

        self._cancel_animate_task = asynchronous.create_task(self._cancel_animate())
        self._cancel_animate_task.add_done_callback(self._cleanup_tasks)

    async def _animate(self):
        while self._do_animate:
            self._adapter.render_and_push(
                is_animating=True,
                do_invalidate_cache=True,
            )
            await asyncio.sleep(1.0 / self._target_fps)

        await asyncio.sleep(1.0)
        self._adapter.render_and_push(
            is_animating=False,
            do_invalidate_cache=True,
        )

    async def _cancel_animate(self):
        await asyncio.sleep(10.0 / self._target_fps)
        self._do_animate = False

    def _cleanup_tasks(self, *_):
        self._animate_task = None
        self._cancel_animate_task = None
