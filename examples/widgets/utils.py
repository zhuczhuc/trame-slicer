from typing import Optional

from slicer import vtkMRMLVolumeNode
from trame_server import Server

from slicer_trame.core import SlicerApp


class _IdName:
    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, obj_type=None):
        return self.name


class StateId:
    current_volume_node_id = _IdName()
    current_layout_name = _IdName()
    file_loading_busy = _IdName()
    vr_slider_value = _IdName()
    vr_slider_min = _IdName()
    vr_slider_max = _IdName()
    vr_presets = _IdName()
    vr_preset_value = _IdName()


def get_current_volume_node(
    server: Server, slicer_app: SlicerApp
) -> Optional[vtkMRMLVolumeNode]:
    node_id = server.state[StateId.current_volume_node_id]
    if not node_id:
        return None
    return slicer_app.scene.GetNodeByID(node_id)
