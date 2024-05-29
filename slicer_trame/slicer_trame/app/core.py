from trame.app import get_server
from trame.decorators import TrameApp, change, controller
from trame.widgets import vuetify3, vtk as vtk_widgets
from trame_vuetify.ui.vuetify3 import SinglePageLayout
from vtkmodules.vtkMRMLCore import vtkMRMLModelStorageNode, vtkMRMLVolumeArchetypeStorageNode

from slicer_trame.app.slice_view import SliceView
from slicer_trame.app.slicer_app import SlicerApp
from slicer_trame.app.threed_view import ThreeDView


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

        self.two_d_view.first_renderer().SetBackground(.0, .0, .0)
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

    @property
    def state(self):
        return self.server.state

    @property
    def ctrl(self):
        return self.server.controller

    @controller.set("reset_resolution")
    def reset_resolution(self):
        self.state.resolution = 6

    @change("resolution")
    def on_resolution_change(self, resolution, **kwargs):
        print(f">>> ENGINE(a): Slider updating resolution to {resolution}")

    def _build_ui(self, *args, **kwargs):
        with SinglePageLayout(self.server) as layout:
            # Toolbar
            layout.title.set_text("Trame / vtk.js")
            with layout.toolbar:
                vuetify3.VSpacer()
                vuetify3.VSlider(  # Add slider
                    v_model=("resolution", 6),  # bind variable with an initial value of 6
                    min=3, max=60, step=1,  # slider range
                    dense=True, hide_details=True,  # presentation setup
                )
                with vuetify3.VBtn(icon=True, click=self.ctrl.reset_camera):
                    vuetify3.VIcon("mdi-crop-free")
                with vuetify3.VBtn(icon=True, click=self.reset_resolution):
                    vuetify3.VIcon("mdi-undo")

            # Main content
            with layout.content:
                with vuetify3.VContainer(fluid=True, classes="pa-0 fill-height"):
                    with vuetify3.VCol(classes="fill-height"):
                        vtk_widgets.VtkLocalView(self.app.threed_view.render_window())
                    with vuetify3.VCol(classes="fill-height"):
                        vtk_widgets.VtkRemoteView(self.app.two_d_view.render_window())

            return layout
