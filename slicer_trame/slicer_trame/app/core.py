from typing import Optional

import vtk

# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import get_server
from trame.decorators import TrameApp, change, controller
from trame.widgets import vuetify3
from trame_rca.widgets.rca import RemoteControlledArea
from trame_vuetify.ui.vuetify3 import SinglePageLayout

# Required for interactor initialization
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from vtkmodules.vtkMRMLCore import (
    vtkMRMLModelStorageNode,
    vtkMRMLVolumeArchetypeStorageNode,
)
from vtkmodules.vtkWebCore import vtkWebApplication

from slicer_trame.components.rca_view_adapter import ViewAdapter
from slicer_trame.slicer import SlicerApp

# This should be unique
HELPER = vtkWebApplication()
HELPER.SetImageEncoding(vtkWebApplication.ENCODING_NONE)
HELPER.SetNumberOfEncoderThreads(4)


class App:
    def __init__(self):
        self.slicer_app = SlicerApp()

        model_storage_node = vtkMRMLModelStorageNode()
        model_storage_node.SetFileName(
            r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\artery.vtk"
        )
        model_storage_node.SetScene(self.slicer_app.scene)
        self.model_node = self.slicer_app.scene.AddNewNodeByClass("vtkMRMLModelNode")
        self.model_node.SetAndObserveStorageNodeID(model_storage_node.GetID())
        model_storage_node.ReadData(self.model_node)

        volume_storage_node = vtkMRMLVolumeArchetypeStorageNode()
        self.volume_node = self.slicer_app.scene.AddNewNodeByClass(
            "vtkMRMLScalarVolumeNode"
        )
        volume_storage_node.SetFileName(
            r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\MRHead.nrrd"
        )
        volume_storage_node.ReadData(self.volume_node)
        self.volume_node.SetAndObserveStorageNodeID(volume_storage_node.GetID())

        self.two_d_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(
            self.volume_node.GetID()
        )

        self.two_d_view.first_renderer().SetBackground(1.0, 1.0, 1.0)
        self.two_d_view.mrml_view_node.SetOrientation("Coronal")
        self.two_d_view.logic.FitSliceToAll()

        self.model_node.CreateDefaultDisplayNodes()
        self.threed_view.schedule_render()
        self.two_d_view.first_renderer().ResetCamera()
        self.two_d_view.schedule_render()

        display = self.logic.CreateDefaultVolumeRenderingNodes(self.volume_node)
        self.volume_node.CreateDefaultDisplayNodes()
        self.volume_node.AddAndObserveDisplayNodeID(display.GetID())


@TrameApp()
class MyTrameApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        self.app = App()
        self.twod_remote_view: Optional[ViewAdapter] = None

        if self.server.hot_reload:
            self.server.controller.on_server_reload.add(self._build_ui)
        self.ui = self._build_ui()

        # Set state variable
        self.state.trame__title = "SlicerTrame"
        self.state.resolution = 6

        self.ctrl.reset_camera = self.reset_camera
        self.ctrl.on_server_ready.add(self.init_rca)

    def init_rca(self, **_):
        # RemoteControllerArea
        self.server.controller.rc_area_register(
            ViewAdapter(self.app.threed_view.render_window(), "3d_view", target_fps=90)
        )
        self.twod_remote_view = ViewAdapter(
            self.app.two_d_view.render_window(), "2d_view", target_fps=90
        )
        self.server.controller.rc_area_register(self.twod_remote_view)

    def reset_camera(self):
        self.app.two_d_view.reset_camera()
        self.app.threed_view.reset_camera()

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @controller.set("reset_slice_offset")
    def reset_slice_offset(self):
        self.app.two_d_view.logic.FitSliceToAll()
        self.state.slice_offset = self.app.two_d_view.logic.GetSliceOffset()

    @change("slice_offset")
    def on_slice_offset_change(self, slice_offset, **kwargs):
        self.app.two_d_view.logic.SetSliceOffset(slice_offset)
        if self.twod_remote_view:
            self.twod_remote_view.still_render()

    def _build_ui(self, *args, **kwargs):
        with SinglePageLayout(self.server) as layout:
            # Toolbar
            layout.title.set_text("Trame / vtk.js")
            with layout.toolbar:
                vuetify3.VSpacer()

                offset_range = [0] * 2
                offset_resolution = vtk.reference(1)
                self.app.two_d_view.logic.GetSliceOffsetRangeResolution(
                    offset_range, offset_resolution
                )
                self.slider = vuetify3.VSlider(  # Add slider
                    v_model=(
                        "slice_offset",
                        self.app.two_d_view.logic.GetSliceOffset(),
                    ),
                    min=offset_range[0],
                    max=offset_range[1],
                    step=float(offset_resolution),  # slider range
                    dense=True,
                    hide_details=True,  # presentation setup
                )

                with vuetify3.VBtn(icon=True, click=self.ctrl.reset_camera):
                    vuetify3.VIcon("mdi-crop-free")
                with vuetify3.VBtn(icon=True, click=self.reset_slice_offset):
                    vuetify3.VIcon("mdi-undo")

            # Main content
            with layout.content:
                with vuetify3.VContainer(fluid=True, classes="pa-0 fill-height"):
                    with vuetify3.VCol(classes="fill-height"):
                        RemoteControlledArea(name="3d_view", display="image")
                    with vuetify3.VCol(classes="fill-height"):
                        RemoteControlledArea(name="2d_view", display="image")

            return layout
