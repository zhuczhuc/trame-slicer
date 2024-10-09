from typing import Optional

from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLVolumeNode
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic
from vtkmodules.vtkSlicerVolumeRenderingModuleLogic import vtkSlicerVolumeRenderingLogic
from vtkmodules.vtkSlicerVolumeRenderingModuleMRML import (
    vtkMRMLVolumeRenderingDisplayNode,
)

from .resources import resources_path


class VolumeRendering:
    """
    Simple facade for volume rendering logic.
    """

    def __init__(self, scene: vtkMRMLScene, app_logic: vtkMRMLApplicationLogic):
        self._logic = vtkSlicerVolumeRenderingLogic()
        self._logic.SetMRMLApplicationLogic(app_logic)
        self._logic.SetMRMLScene(scene)
        self._logic.SetModuleShareDirectory(resources_path().as_posix())
        self._logic.ChangeVolumeRenderingMethod(
            "vtkMRMLGPURayCastVolumeRenderingDisplayNode"
        )

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
        display: Optional[vtkMRMLVolumeRenderingDisplayNode],
        preset_name: str,
    ):
        if not display:
            return

        preset_names = self.preset_names()
        if not preset_names:
            return

        if preset_name not in preset_names:
            preset_name = preset_names[0]

        display.GetVolumePropertyNode().Copy(self._logic.GetPresetByName(preset_name))

    def get_vr_display_node(
        self,
        volume_node: vtkMRMLVolumeNode,
    ) -> Optional[vtkMRMLVolumeRenderingDisplayNode]:
        return self._logic.GetFirstVolumeRenderingDisplayNode(volume_node)

    def has_vr_display_node(self, volume_node: vtkMRMLVolumeNode) -> bool:
        return self.get_vr_display_node(volume_node) is not None

    def preset_names(self) -> list[str]:
        preset_nodes = self._logic.GetPresetsScene().GetNodes()
        return [
            preset_nodes.GetItemAsObject(i_node).GetName()
            for i_node in range(preset_nodes.GetNumberOfItems())
        ]
