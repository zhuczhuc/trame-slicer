from enum import Flag, auto
from typing import Callable, Optional

from slicer import vtkMRMLVolumePropertyNode
from vtkmodules.vtkCommonDataModel import vtkPiecewiseFunction
from vtkmodules.vtkRenderingCore import vtkColorTransferFunction, vtkVolumeProperty


class VRShiftMode(Flag):
    OPACITY = auto()
    COLOR = auto()
    BOTH = OPACITY | COLOR


class VolumeProperty:
    """
    Thin facade for volume property node.
    Allows more pythonic access to the scalar / opacity properties of a volume rendering display node.
    """

    def __init__(self, volume_property_node: Optional[vtkMRMLVolumePropertyNode]):
        self._property_node = volume_property_node or vtkMRMLVolumePropertyNode()

    @property
    def volume_property(self) -> vtkVolumeProperty:
        return self._property_node.GetVolumeProperty() or vtkVolumeProperty()

    @property
    def property_node(self):
        return self._property_node

    @property
    def opacity_map(self) -> vtkPiecewiseFunction:
        return self.volume_property.GetScalarOpacity()

    @property
    def color_map(self) -> vtkColorTransferFunction:
        return self.volume_property.GetRGBTransferFunction()

    def get_color_map_values(self) -> list[list[float]]:
        return self._get_map_values(self.color_map, 6)

    def get_opacity_map_values(self) -> list[list[float]]:
        return self._get_map_values(self.opacity_map, 4)

    def set_color_map_values(self, values: list[list[float]]):
        self._set_map_values(
            self.color_map,
            self.color_map.AddRGBPoint,
            values,
        )

    def set_opacity_values(self, values: list[list[float]]):
        self._set_map_values(
            self.opacity_map,
            self.opacity_map.AddPoint,
            values,
        )

    def shift_color_map(self, shift: float) -> None:
        self.set_color_map_values(
            self.shift_values(self.get_opacity_map_values(), shift)
        )

    def shift_opacity_map(self, shift: float) -> None:
        self.set_opacity_values(self.shift_values(self.get_opacity_map_values(), shift))

    def get_effective_range(self) -> tuple[float, float]:
        if not self._property_node.CalculateEffectiveRange():
            return -1, 1

        effective_range = self._property_node.GetEffectiveRange()
        transfer_function_width = effective_range[1] - effective_range[0]
        return -transfer_function_width, transfer_function_width

    @staticmethod
    def shift_values(values, shift):
        values = values or []
        return [[value[0] + shift, *value[1:]] for value in values]

    def set_vr_shift(
        self,
        shift: float,
        shift_mode: VRShiftMode,
        ref_prop: Optional["VolumeProperty"] = None,
    ):
        ref_prop = ref_prop or self
        if shift_mode & VRShiftMode.COLOR:
            self.set_color_map_values(
                self.shift_values(ref_prop.get_color_map_values(), shift)
            )

        if shift_mode & VRShiftMode.OPACITY:
            self.set_opacity_values(
                self.shift_values(ref_prop.get_opacity_map_values(), shift)
            )

    @classmethod
    def _get_map_values(cls, transfer_fun, array_size: int) -> Optional[list[list]]:
        values = []
        if not transfer_fun:
            return None

        for i_pt in range(transfer_fun.GetSize()):
            array = [0] * array_size
            transfer_fun.GetNodeValue(i_pt, array)
            values.append(array)
        return values

    @classmethod
    def _set_map_values(
        cls,
        transfer_fun,
        add_fun: Callable,
        values: Optional[list[list[float]]],
    ):
        if not all([transfer_fun, values]):
            return

        transfer_fun.RemoveAllPoints()
        for value in values:
            add_fun(*value)

        return values
