from abc import ABC, abstractmethod
from typing import Callable, Optional

from slicer import vtkMRMLInteractionEventData


class AbstractViewInteractor(ABC):
    def __init__(self):
        self.render_callback: Optional[Callable] = None

    @abstractmethod
    def process_event(self, event_data: vtkMRMLInteractionEventData) -> bool:
        pass

    def trigger_render_callback(self) -> None:
        if self.render_callback:
            self.render_callback()
