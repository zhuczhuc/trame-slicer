from trame_client.widgets.core import Template
from trame_server import Server
from trame_vuetify.widgets.vuetify3 import VCard, VCardText, VMenu, VRow

from slicer_trame.core import SlicerApp

from .control_button import ControlButton
from .vr_preset_select import VRPresetSelect
from .vr_shift_slider import VRShiftSlider


class VolumePropertyButton(VMenu):
    def __init__(self, server: Server, slicer_app: SlicerApp):
        super().__init__(location="end", close_on_content_click=False)
        with self:
            with Template(v_slot_activator="{ props }"):
                ControlButton(
                    name="Volume Properties", icon="mdi-tune-variant", v_bind="props"
                )

            with VCard(), VCardText():
                with VRow():
                    VRPresetSelect(server=server, slicer_app=slicer_app)
                with VRow():
                    VRShiftSlider(server=server, slicer_app=slicer_app)
