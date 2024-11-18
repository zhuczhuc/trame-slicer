import asyncio
from math import floor
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Optional

from trame.app import get_server
from trame.app.file_upload import ClientFile
from trame.decorators import TrameApp, change
from trame.widgets import vuetify3
from trame_client.widgets.html import Div, Input, Span
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from trame_vuetify.ui.vuetify3 import SinglePageLayout
from trame_vuetify.widgets.vuetify3 import (
    Template,
    VBtn,
    VCard,
    VCardText,
    VIcon,
    VMenu,
    VProgressCircular,
    VRadio,
    VRadioGroup,
    VTooltip,
)
from vtkmodules.vtkCommonCore import vtkCollection

from slicer_trame.core import LayoutManager, SlicerApp
from slicer_trame.rca_view import register_rca_factories


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
    def __init__(
        self,
        *,
        layout_list,
        server: Server,
        on_load_files: Callable[[list[dict]], None],
        **kwargs,
    ):
        super().__init__(
            classes="bg-grey-darken-4 d-flex flex-column align-center", **kwargs
        )

        with self:
            files_input_ref = "open_files_input"

            def create_load_task(*a, **kw):
                server.state["file_loading_busy"] = True
                server.state.flush()

                async def load():
                    await asyncio.sleep(1)
                    try:
                        on_load_files(*a, **kw)
                    finally:
                        server.state["file_loading_busy"] = False
                        server.state.flush()

                create_task(load())

            Input(
                type="file",
                multiple=True,
                change=(
                    "file_loading_busy = true;"
                    "trigger('"
                    f"{server.controller.trigger_name(create_load_task)}"
                    "', [$event.target.files]"
                    ")"
                ),
                __events=["change"],
                style="display: none;",
                ref=files_input_ref,
            )
            ControlButton(
                name="Open files",
                icon="mdi-folder-open",
                click=lambda: server.js_call(ref=files_input_ref, method="click"),
                v_if=("!file_loading_busy",),
            )
            VProgressCircular(v_if=("file_loading_busy",), indeterminate=True, size=24)
            LayoutButton(layout_list)
            ControlButton(
                name="Place Points",
                icon="mdi-dots-square",
                click=server.controller.markups_clicked,
            )


@TrameApp()
class MyTrameSlicerApp:
    def __init__(self, server=None):
        self._server = get_server(server, client_type="vue3")
        self._server.state.setdefault("file_loading_busy", False)
        self._server.controller.markups_clicked = self.on_markups_clicked

        self._markups_node = None

        self._slicer_app = SlicerApp()

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

    def on_markups_clicked(self):
        if self._markups_node is None:
            self._markups_node = self._slicer_app.scene.AddNewNodeByClass(
                "vtkMRMLMarkupsFiducialNode"
            )

        self._slicer_app.markups_logic.SetActiveList(self._markups_node)
        self._slicer_app.markups_logic.StartPlaceMode(True)

    @change("current_layout_name")
    def on_current_layout_changed(self, current_layout_name, *args, **kwargs):
        self._layout_manager.set_layout(current_layout_name)

    @property
    def server(self):
        return self._server

    def _on_load_files(self, files: list[dict]) -> None:
        if not files:
            return

        # Remove previous volume nodes
        vol_nodes: vtkCollection = self._slicer_app.scene.GetNodesByClass(
            "vtkMRMLVolumeNode"
        )
        for i_vol in range(vol_nodes.GetNumberOfItems()):
            self._slicer_app.scene.RemoveNode(vol_nodes.GetItemAsObject(i_vol))

        # Load new volumes and display the first one
        with TemporaryDirectory() as tmp_dir:
            file_list = []
            for file in files:
                file_helper = ClientFile(file)
                file_path = Path(tmp_dir) / file_helper.name
                with open(file_path, "wb") as f:
                    f.write(file_helper.content)
                file_list.append(file_path.as_posix())

            volumes = self._slicer_app.io_manager.load_volumes(file_list)
            if not volumes:
                return

            # Show the largest volume
            def bounds_volume(v):
                b = [0] * 6
                v.GetImageData().GetBounds(b)
                return (b[1] - b[0]) * (b[3] - b[2]) * (b[5] - b[4])

            volumes = list(sorted(volumes, key=bounds_volume))
            self._slicer_app.display_manager.show_volume(
                volumes[-1],
                vr_preset="CT-Coronary-Arteries-3",
                do_reset_views=True,
            )

    def _build_ui(self, *args, **kwargs):
        with SinglePageLayout(self._server) as self.ui:
            self.ui.root.theme = "dark"

            # Toolbar
            self.ui.title.set_text("Slicer Trame")

            with self.ui.toolbar:
                vuetify3.VSpacer()

            # Main content
            with self.ui.content:
                with Div(classes="fill-height d-flex flex-row flex-grow-1"):
                    ToolsStrip(
                        layout_list=self._layout_manager.get_layout_ids(),
                        server=self.server,
                        on_load_files=self._on_load_files,
                    )
                    self._server.ui.layout_grid(self.ui)


def main(server=None, **kwargs):
    app = MyTrameSlicerApp(server)
    app.server.start(**kwargs)


if __name__ == "__main__":
    main()
