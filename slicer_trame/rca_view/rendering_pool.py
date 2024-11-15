from concurrent.futures import ProcessPoolExecutor

from slicer_trame.utils.singleton_meta import Singleton


class RenderingPool(metaclass=Singleton):
    def __init__(self):
        self._pool = ProcessPoolExecutor()

    @classmethod
    def get_singleton(cls) -> ProcessPoolExecutor:
        return cls()._pool
