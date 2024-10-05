from concurrent.futures.process import ProcessPoolExecutor
from typing import Any

from vtkmodules.vtkWebCore import vtkWebApplication


class Singleton(type):
    _instances: dict[type, Any] = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class WebApplication(metaclass=Singleton):
    def __init__(self):
        self._web_app = vtkWebApplication()
        self._web_app.SetImageEncoding(vtkWebApplication.ENCODING_NONE)
        self._web_app.SetNumberOfEncoderThreads(4)

    @classmethod
    def get_singleton(cls):
        return cls()._web_app


class RenderingPool(metaclass=Singleton):
    def __init__(self):
        self._pool = ProcessPoolExecutor()

    @classmethod
    def get_singleton(cls) -> ProcessPoolExecutor:
        return cls()._pool
