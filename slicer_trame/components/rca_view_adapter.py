import json

from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter

from slicer_trame.slicer import AbstractView

from .rca_render_scheduler import RcaRenderScheduler


class RcaViewAdapter:
    """
    Adapter for a Remote controlled area
    Based on implementation : https://github.com/Kitware/trame-rca/blob/master/examples/00_cone/app.py
    """

    def __init__(
        self,
        view: AbstractView,
        name: str,
        target_fps: float = 30.0,
        interactive_quality: int = 50,
    ):
        self._view = view
        self._view.set_scheduled_render(
            RcaRenderScheduler(
                self.push,
                view.render_window(),
                target_fps=target_fps,
                interactive_quality=interactive_quality,
            )
        )
        self._window = view.render_window()
        self.area_name = name
        self.streamer = None
        self._prev_data_m_time = None
        self._interactive_quality = interactive_quality

        self._iren = self._window.GetInteractor()
        self._iren.EnableRenderOff()
        self._window.ShowWindowOff()
        self._press_set = set()

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        # Resize to one pixel min to avoid rendering problems in VTK
        width = max(1, int(size.get("w", 300)))
        height = max(1, int(size.get("h", 300)))
        self._iren.UpdateSize(width, height)
        self._view.schedule_render()

    def push(self, content, meta: dict):
        if not self.streamer:
            return

        if content is None:
            return

        self.streamer.push_content(self.area_name, meta, content)

    def do_discard_extra_release_event(self, event):
        """
        Ignores mouse release events which have not been preceded by a previous mouse press.
        """
        event_type = event["type"]
        if "Press" in event_type:
            self._press_set.add(event_type)
            return False

        if not event_type.endswith("Release"):
            return False

        press_event = event_type.replace("Release", "Press")
        if press_event in self._press_set:
            self._press_set.remove(press_event)
            return False

        return True

    def on_interaction(self, _, event):
        event_type = event["type"]
        if event_type in ["StartInteractionEvent", "EndInteractionEvent"]:
            return

        if self.do_discard_extra_release_event(event):
            return

        vtkRemoteInteractionAdapter.ProcessEvent(self._iren, json.dumps(event))
