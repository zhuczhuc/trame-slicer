import asyncio
import json
import time

import vtk
# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import vtkmodules.vtkRenderingOpenGL2  # noqa
from trame.app import asynchronous, get_server
from trame.decorators import TrameApp, change, controller
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify3, vtklocal as vtk_widgets
from trame_rca.widgets.rca import RemoteControlledArea
from trame_vuetify.ui.vuetify3 import SinglePageLayout
# Required for interactor initialization
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa
from vtkmodules.vtkMRMLCore import vtkMRMLModelStorageNode, vtkMRMLVolumeArchetypeStorageNode
from vtkmodules.vtkWebCore import vtkRemoteInteractionAdapter, vtkWebApplication

from slicer_trame.app.slice_view import SliceView
from slicer_trame.app.slicer_app import SlicerApp
from slicer_trame.app.threed_view import ThreeDView

# Activate a RemoteControlledArea : https://github.com/Kitware/trame-rca/blob/master/examples/00_cone/app.py

# This should be unique
HELPER = vtkWebApplication()
HELPER.SetImageEncoding(vtkWebApplication.ENCODING_NONE)
HELPER.SetNumberOfEncoderThreads(4)


class ViewAdapter:
    def __init__(self, window, name, target_fps=30):
        self._view = window
        self.area_name = name
        self.streamer = None
        self.last_meta = None
        self.animating = False
        self.target_fps = target_fps

        self._iren = window.GetInteractor()
        self._iren.EnableRenderOff()
        self._view.ShowWindowOff()

    def _get_metadata(self):
        return dict(
            type="image/jpeg",  # mime time
            codec="",  # video codec, not relevant here
            w=self._view.GetSize()[0],
            h=self._view.GetSize()[1],
            st=int(time.time_ns() / 1000000),
            key=("key"),  # jpegs are always keyframes
        )

    async def _animate(self):
        mtime = 0
        while self.animating:
            data = HELPER.InteractiveRender(self._view)
            if data is not None and mtime != data.GetMTime():
                mtime = data.GetMTime()
                self.push(memoryview(data), self._get_metadata())
                await asyncio.sleep(1.0 / self.target_fps)
            await asyncio.sleep(0)

        HELPER.InvalidateCache(self._view)
        content = memoryview(HELPER.StillRender(self._view))
        self.push(content, self._get_metadata())

    def set_streamer(self, stream_manager):
        self.streamer = stream_manager

    def update_size(self, origin, size):
        width = int(size.get("w", 300))
        height = int(size.get("h", 300))
        self._view.SetSize(width, height)
        content = memoryview(HELPER.StillRender(self._view))
        self.push(content, self._get_metadata())

    def push(self, content, meta=None):
        if meta is not None:
            self.last_meta = meta
        if content is None:
            return
        self.streamer.push_content(self.area_name, self.last_meta, content)

    def on_interaction(self, origin, event):
        event_type = event["type"]
        if event_type == "StartInteractionEvent":
            if not self.animating:
                self.animating = True
                asynchronous.create_task(self._animate())
        elif event_type == "EndInteractionEvent":
            self.animating = False
        else:
            event_str = json.dumps(event)
            status = vtkRemoteInteractionAdapter.ProcessEvent(self._iren, event_str)

            # Force Render next time InteractiveRender is called
            if status:
                HELPER.InvalidateCache(self._view)


class App:
    def __init__(self):
        self.slicer_app = SlicerApp()
        self.threed_view = ThreeDView(self.slicer_app, "ThreeDView")
        self.two_d_view = SliceView(self.slicer_app, "SliceView")

        model_storage_node = vtkMRMLModelStorageNode()
        model_storage_node.SetFileName(r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\artery.vtk")
        model_storage_node.SetScene(self.slicer_app.scene)
        self.model_node = self.slicer_app.scene.AddNewNodeByClass("vtkMRMLModelNode")
        self.model_node.SetAndObserveStorageNodeID(model_storage_node.GetID())
        model_storage_node.ReadData(self.model_node)

        volume_storage_node = vtkMRMLVolumeArchetypeStorageNode()
        self.volume_node = self.slicer_app.scene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
        volume_storage_node.SetFileName(r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\MRHead.nrrd")
        volume_storage_node.ReadData(self.volume_node)
        self.volume_node.SetAndObserveStorageNodeID(volume_storage_node.GetID())

        self.two_d_view.logic.GetSliceCompositeNode().SetBackgroundVolumeID(self.volume_node.GetID())

        self.two_d_view.first_renderer().SetBackground(1.0, 1.0, 1.0)
        self.two_d_view.mrml_view_node.SetOrientation("Coronal")
        self.two_d_view.logic.FitSliceToAll()

        self.model_node.CreateDefaultDisplayNodes()
        self.threed_view.render()
        self.two_d_view.first_renderer().ResetCamera()
        self.two_d_view.render()


@TrameApp()
class MyTrameApp:
    def __init__(self, server=None):
        self.server = get_server(server, client_type="vue3")
        self.app = App()

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
        view_handler = ViewAdapter(self.app.threed_view.render_window(), "view", target_fps=30)
        self.server.controller.rc_area_register(view_handler)

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
        # self.twod_remote_view.update()

    def _build_ui(self, *args, **kwargs):
        with SinglePageLayout(self.server) as layout:
            # Toolbar
            layout.title.set_text("Trame / vtk.js")
            with layout.toolbar:
                vuetify3.VSpacer()

                offset_range = [0] * 2
                offset_resolution = vtk.reference(1)
                self.app.two_d_view.logic.GetSliceOffsetRangeResolution(offset_range, offset_resolution)
                self.slider = vuetify3.VSlider(  # Add slider
                    v_model=("slice_offset", self.app.two_d_view.logic.GetSliceOffset()),
                    min=offset_range[0], max=offset_range[1], step=float(offset_resolution),  # slider range
                    dense=True, hide_details=True,  # presentation setup
                )

                with vuetify3.VBtn(icon=True, click=self.ctrl.reset_camera):
                    vuetify3.VIcon("mdi-crop-free")
                with vuetify3.VBtn(icon=True, click=self.reset_slice_offset):
                    vuetify3.VIcon("mdi-undo")

            # Main content
            with layout.content:
                with vuetify3.VContainer(fluid=True, classes="pa-0 fill-height"):
                    with vuetify3.VCol(classes="fill-height"):
                        RemoteControlledArea(name="view", display="image")
                    # with vuetify3.VCol(classes="fill-height"):
                    #     self.twod_remote_view = vtk_widgets.LocalView(self.app.two_d_view.render_window())

            return layout
