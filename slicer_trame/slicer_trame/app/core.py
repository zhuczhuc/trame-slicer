from pathlib import Path
from typing import Optional

from trame.app import get_server
from trame.decorators import TrameApp
from trame.widgets import client, vuetify3
from trame_vuetify.ui.vuetify3 import SinglePageWithDrawerLayout

from slicer_trame.components.rca_slicer_view_factory import register_rca_factories
from slicer_trame.slicer import LayoutManager, SlicerApp
from slicer_trame.slicer.resources import get_css_path


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
        self._layout_manager.set_layout("Axial Primary")

        dcm_files = [
            p.as_posix()
            for p in Path(
                r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\slicer_trame\tests\data\mr_head_dcm"
            ).glob("*.dcm")
        ]
        volumes = self._slicer_app.io_manager.load_volumes(dcm_files)
        if volumes:
            self._slicer_app.display_manager.show_volume(
                volumes[0],
                vr_preset="MR-Default",
            )

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
                self._server.ui.layout_grid(self.ui)

            self.ui.footer.clear()
