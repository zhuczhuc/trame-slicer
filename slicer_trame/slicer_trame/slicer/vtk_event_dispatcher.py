from itertools import count
from typing import Callable, Optional, Union
from weakref import WeakMethod

from _weakref import ref
from vtkmodules.vtkCommonCore import vtkObject


class VtkEventDispatcher:
    """
    Responsible for connecting multiple events to one output.
    Information forwarded through this output is defined by the user.
    """

    def __init__(self):
        self._weak_obs: list[WeakMethod] = []
        self._inst_obs: set[Callable] = set()
        self._vtk_obj: dict[int, tuple[ref, int]] = dict()
        self._obs_id = count()
        self._trigger_args = []
        self._trigger_kwargs = {}

    def attach_vtk_observer(
        self,
        vtk_obj: vtkObject,
        observed_event: Union[int, str],
    ) -> int:
        vtk_obj_obs_id = vtk_obj.AddObserver(observed_event, self._trigger_dispatch)
        _obs_id = next(self._obs_id)
        self._vtk_obj[_obs_id] = (ref(vtk_obj), vtk_obj_obs_id)
        return _obs_id

    def detach_vtk_observer(self, obs_id: Optional[int]) -> None:
        if obs_id not in self._vtk_obj:
            return

        obj, obs_id = self._vtk_obj[obs_id]
        obj = obj()
        if obj is None:
            return

        obj.RemoveObserver(obs_id)

    def add_dispatch_observer(self, obs: Callable) -> None:
        try:
            self._weak_obs.append(WeakMethod(obs))
        except TypeError:
            self._inst_obs.add(obs)

    def remove_dispatch_observer(self, obs: Callable) -> None:
        self._weak_obs = [_obs for _obs in self._weak_obs if _obs() != obs]
        if obs in self._inst_obs:
            self._inst_obs.remove(obs)

    def set_dispatch_information(self, *args, **kwargs) -> None:
        self._trigger_args = args
        self._trigger_kwargs = kwargs

    def _trigger_dispatch(self, *_) -> None:
        observers = [obs() for obs in self._weak_obs if obs() is not None] + list(
            self._inst_obs
        )
        for obs in observers:
            obs(*self._trigger_args, **self._trigger_kwargs)
