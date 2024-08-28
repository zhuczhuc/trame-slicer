from math import floor
from pathlib import Path
from typing import Callable, Optional

from trame.app import get_server
from trame.decorators import TrameApp, change
from trame.widgets import client, vuetify3
from trame_client.widgets.html import Div, Span
from trame_vuetify.ui.vuetify3 import SinglePageWithDrawerLayout
from trame_vuetify.widgets.vuetify3 import (
    Template,
    VBtn,
    VCard,
    VCardText,
    VIcon,
    VMenu,
    VRadio,
    VRadioGroup,
    VTooltip,
)

from slicer_trame.components.rca_view_factory import register_rca_factories
from slicer_trame.slicer import LayoutManager, SlicerApp
from slicer_trame.slicer.resources import get_css_path


class ControlButton(VBtn):
    def __init__(
        self,
        *,
        name: str,
        icon: str,
        click: Optional[Callable] = None,
        size: int = 40,
        **kwargs,
    ) -> None:
        super().__init__(
            variant="text",
            rounded=0,
            height=size,
            width=size,
            min_height=size,
            min_width=size,
            click=click,
            **kwargs,
        )

        icon_size = floor(0.6 * size)

        with self:
            VIcon(icon, size=icon_size)
            with VTooltip(
                activator="parent",
                transition="slide-x-transition",
                location="right",
            ):
                Span(f"{name}")


class LayoutButton(VMenu):
    def __init__(self, layout_list):
        super().__init__(location="right", close_on_content_click=True)
        with self:
            with Template(v_slot_activator="{props}"):
                ControlButton(
                    v_bind="props",
                    icon="mdi-view-dashboard",
                    name="Layouts",
                )

            with VCard():
                with VCardText():
                    with VRadioGroup(
                        v_model="current_layout_name", classes="mt-0", hide_details=True
                    ):
                        for layout in layout_list:
                            VRadio(label=layout, value=layout)


class ToolsStrip(Div):
    def __init__(self, *, layout_list, **kwargs):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center", **kwargs
        )

        with self:
            ControlButton(name="Open files", icon="mdi-folder-open", click=lambda: None)
            LayoutButton(layout_list)


@TrameApp()
class MyTrameSlicerApp:
    def __init__(self, server=None, css_file_path: Optional[Path] = None):
        self._server = get_server(server, client_type="vue3")
        self._slicer_app = SlicerApp()
        self._css_file = Path(css_file_path or get_css_path())

        register_rca_factories(self._slicer_app.view_manager, self._server)

        self._layout_manager = LayoutManager(
            self._slicer_app.scene,
            self._slicer_app.view_manager,
            self._server.ui.layout_grid,
        )

        self._layout_manager.register_layout_dict(
            LayoutManager.default_grid_configuration()
        )

        self._build_ui()

        default_layout = "Axial Primary"
        self.server.state.setdefault("current_layout_name", default_layout)
        self._layout_manager.set_layout(default_layout)

        dcm_files = [
            p.as_posix()
            for p in Path(
                r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\slicer_trame\tests\data\mr_head_dcm"
            ).glob("*.dcm")
        ]
        volumes = self._slicer_app.io_manager.load_volumes(dcm_files)
        if volumes:
            self._slicer_app.display_manager.show_volume(
                volumes[0], vr_preset="MR-Default", fit_view_to_content=True
            )

    @change("current_layout_name")
    def on_current_layout_changed(self, current_layout_name, *args, **kwargs):
        self._layout_manager.set_layout(current_layout_name)

    @property
    def server(self):
        return self._server

    def _build_ui(self, *args, **kwargs):
        with SinglePageWithDrawerLayout(self._server) as self.ui:
            if self._css_file.is_file():
                client.Style(self._css_file.read_text())

            self.ui.root.theme = "dark"

            # Toolbar
            self.ui.title.set_text("Slicer Trame")

            with self.ui.toolbar:
                vuetify3.VSpacer()

            # Main content
            with self.ui.content:
                with Div(classes="fill-height d-flex flex-row flex-grow-1"):
                    ToolsStrip(layout_list=self._layout_manager.get_layout_ids())
                    self._server.ui.layout_grid(self.ui)

            self.ui.footer.clear()
