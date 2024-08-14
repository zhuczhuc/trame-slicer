import asyncio
import json
import time
from typing import Optional

from trame.app import asynchronous
from vtkmodules.vtkRenderingCore import vtkRenderWindow
from vtkmodules.vtkWebCore import vtkWebApplication, vtkRemoteInteractionAdapter

from slicer_trame.components.web_application import WebApplication


class ViewAdapter:
    """
    Adapter for a Remote controlled area
    Based on implementation : https://github.com/Kitware/trame-rca/blob/master/examples/00_cone/app.py
    """

    def __init__(
        self,
        window: vtkRenderWindow,
        name: str,
        web_application: Optional[vtkWebApplication] = None,
        target_fps: int = 30,
    ):
        self._view = window
        self.area_name = name
        self.streamer = None
        self.last_meta = None
        self.animating = False
        self.is_updating = False
        self.target_fps = target_fps

        self._iren = window.GetInteractor()
        self._iren.EnableRenderOff()
        self._view.ShowWindowOff()
        self._web_application = web_application or WebApplication.get_singleton()

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # mime time
            codec="",  # video codec, not relevant here
            w=self._view.GetSize()[0],
            h=self._view.GetSize()[1],
            st=int(time.time_ns() / 1000000),
            key=("key"),  # jpegs are always keyframes
        )

    async def _animate(self):
        mtime = 0
        while self.animating:
            data = self._web_application.InteractiveRender(self._view)
            if data is not None and mtime != data.GetMTime():
                mtime = data.GetMTime()
                self.push(memoryview(data), self._get_metadata())
                await asyncio.sleep(1.0 / self.target_fps)
            await asyncio.sleep(0)

        self._web_application.InvalidateCache(self._view)
        content = memoryview(self._web_application.StillRender(self._view))
        self.push(content, self._get_metadata())

    def still_render(self, *_):
        if self.animating or self.is_updating:
            return

        self.is_updating = True
        data = (
            self._web_application.StillRender(self._view)
            if not self.animating
            else self._web_application.InteractiveRender(self._view)
        )
        self.push(memoryview(data), self._get_metadata())
        self.is_updating = False

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        width = int(size.get("w", 300))
        height = int(size.get("h", 300))
        self._view.SetSize(width, height)
        self.still_render()

    def push(self, content, meta=None):
        if meta is not None:
            self.last_meta = meta
        if content is None:
            return
        self.streamer.push_content(self.area_name, self.last_meta, content)

    def on_interaction(self, origin, event):
        event_type = event["type"]
        if event_type == "StartInteractionEvent":
            if not self.animating:
                self.animating = True
                asynchronous.create_task(self._animate())
        elif event_type == "EndInteractionEvent":
            self.animating = False
            self.still_render()
        else:
            event_str = json.dumps(event)
            status = vtkRemoteInteractionAdapter.ProcessEvent(self._iren, event_str)

            # Force Render next time InteractiveRender is called
            if status:
                self._web_application.InvalidateCache(self._view)
