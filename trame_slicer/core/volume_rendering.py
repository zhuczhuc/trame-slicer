from slicer import (
    vtkMRMLApplicationLogic,
    vtkMRMLScene,
    vtkMRMLVolumeNode,
    vtkMRMLVolumePropertyNode,
    vtkMRMLVolumeRenderingDisplayNode,
    vtkSlicerVolumeRenderingLogic,
)

from .volume_property import VolumeProperty, VRShiftMode


class VolumeRendering:
    """
    Simple facade for volume rendering logic.
    """

    def __init__(
        self,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
        share_directory: str,
    ):
        self._logic = vtkSlicerVolumeRenderingLogic()
        self._logic.SetMRMLApplicationLogic(app_logic)
        self._logic.SetMRMLScene(scene)
        self._logic.ChangeVolumeRenderingMethod(
            "vtkMRMLGPURayCastVolumeRenderingDisplayNode"
        )
        self._logic.SetModuleShareDirectory(share_directory)

    def create_display_node(
        self,
        volume_node: vtkMRMLVolumeNode,
        preset_name: str = "",
    ) -> vtkMRMLVolumeRenderingDisplayNode:
        display = self.get_vr_display_node(volume_node)
        if display:
            return display

        display = self._logic.CreateDefaultVolumeRenderingNodes(volume_node)
        self.apply_preset(display, preset_name)
        volume_node.GetDisplayNode().SetVisibility(True)
        display.SetVisibility(True)
        return display

    def apply_preset(
        self,
        display: vtkMRMLVolumeRenderingDisplayNode | None,
        preset_name: str,
    ):
        if not display:
            return

        display.GetVolumePropertyNode().Copy(
            self.get_preset_property(preset_name).property_node
        )

    def get_preset_property(self, preset_name) -> VolumeProperty:
        preset_names = self.preset_names()
        if not preset_names:
            return VolumeProperty(None)

        if preset_name not in preset_names:
            preset_name = preset_names[0]

        return VolumeProperty(self._logic.GetPresetByName(preset_name))

    def get_vr_display_node(
        self,
        volume_node: vtkMRMLVolumeNode,
    ) -> vtkMRMLVolumeRenderingDisplayNode | None:
        return self._logic.GetFirstVolumeRenderingDisplayNode(volume_node)

    def has_vr_display_node(self, volume_node: vtkMRMLVolumeNode) -> bool:
        return self.get_vr_display_node(volume_node) is not None

    def _get_preset_nodes(self) -> list[vtkMRMLVolumePropertyNode]:
        preset_nodes_collection = self._logic.GetPresetsScene().GetNodes()
        return [
            preset_nodes_collection.GetItemAsObject(i_node)
            for i_node in range(preset_nodes_collection.GetNumberOfItems())
        ]

    def preset_names(self) -> list[str]:
        preset_nodes = self._get_preset_nodes()
        return [preset_node.GetName() for preset_node in preset_nodes]

    def get_preset_node(self, preset_name: str) -> vtkMRMLVolumePropertyNode | None:
        preset_nodes = self._get_preset_nodes()
        for i in range(len(preset_nodes)):
            if preset_nodes[i].GetName() == preset_name:
                return preset_nodes[i]
        return None

    def set_absolute_vr_shift_from_preset(
        self,
        volume_node: vtkMRMLVolumeNode,
        preset_name: str,
        shift: float,
        shift_mode: VRShiftMode = VRShiftMode.BOTH,
    ) -> None:
        """
        Shift the volume rendering opacity and colors by a given value.
        The shift is a scalar value representing how much the preset should be
        moved compared to a preset default.

        Which

        See also:
            :ref: `set_relative_vr_shift`
        """
        vr_prop = self.get_volume_node_property(volume_node)
        vr_prop.set_vr_shift(shift, shift_mode, self.get_preset_property(preset_name))

    def set_relative_vr_shift(
        self,
        volume_node: vtkMRMLVolumeNode,
        shift: float,
        shift_mode: VRShiftMode = VRShiftMode.BOTH,
    ) -> None:
        """
        Shift the volume rendering opacity and colors by a given value for the current scalar/opacity values.

        See also:
            :ref: `set_absolute_vr_shift_from_preset`
        """
        vr_prop = self._get_vr_volume_property(self.get_vr_display_node(volume_node))
        vr_prop.set_vr_shift(shift, shift_mode)

    def get_vr_shift_range(self, volume_node: vtkMRMLVolumeNode) -> tuple[float, float]:
        return self.get_volume_node_property(volume_node).get_effective_range()

    def get_preset_vr_shift_range(self, preset_name: str) -> tuple[float, float]:
        return self.get_preset_property(preset_name).get_effective_range()

    def get_volume_node_property(
        self, volume_node: vtkMRMLVolumeNode
    ) -> VolumeProperty:
        return self._get_vr_volume_property(self.get_vr_display_node(volume_node))

    @classmethod
    def _get_vr_volume_property(
        cls, vr_display_node: vtkMRMLVolumeRenderingDisplayNode | None
    ) -> VolumeProperty:
        return VolumeProperty(
            vr_display_node.GetVolumePropertyNode() if vr_display_node else None
        )
