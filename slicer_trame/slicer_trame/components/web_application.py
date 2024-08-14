from vtkmodules.vtkWebCore import vtkWebApplication


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class WebApplication(metaclass=Singleton):
    def __init__(self):
        self._web_app = vtkWebApplication()

    @classmethod
    def get_singleton(cls):
        return cls()._web_app
