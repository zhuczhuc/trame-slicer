from abc import abstractmethod
from dataclasses import dataclass
from typing import Callable

from trame_client.widgets.html import Div
from trame_rca.widgets.rca import RemoteControlledArea
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from trame_vuetify.widgets.vuetify3 import VBtn, VIcon, VSlider, VTooltip
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from slicer_trame.slicer.abstract_view import AbstractView, AbstractViewChild
from slicer_trame.slicer.slice_view import SliceView
from slicer_trame.slicer.threed_view import ThreeDView
from slicer_trame.slicer.view_factory import IViewFactory

from ..slicer.view_layout_definition import ViewLayoutDefinition, ViewType
from ..slicer.view_manager import ViewManager
from .rca_view_adapter import RcaViewAdapter
from .view_layout import ViewLayout


@dataclass
class RcaView:
    vuetify_view: RemoteControlledArea
    slicer_view: AbstractViewChild
    view_adapter: RcaViewAdapter


def register_rca_factories(view_manager: ViewManager, server: Server) -> None:
    """
    Helper function to register all RCA factories to a view manager.
    """
    for f_type in [RemoteSliceViewFactory, RemoteThreeDViewFactory]:
        view_manager.register_factory(f_type(server))


class RemoteViewFactory(IViewFactory):
    def __init__(self, server: Server, view_ctor: Callable, view_type: ViewType):
        super().__init__()
        self._server = server
        self._view_ctor = view_ctor
        self._view_type = view_type

    def _get_slicer_view(self, view: RcaView) -> AbstractView:
        return view.slicer_view

    def can_create_view(self, view: ViewLayoutDefinition) -> bool:
        return view.type == self._view_type

    def _create_view(
        self,
        view: ViewLayoutDefinition,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ) -> RcaView:
        view_id = view.singleton_tag
        slicer_view: AbstractView = self._view_ctor(
            scene=scene,
            app_logic=app_logic,
            name=view_id,
        )

        slicer_view.set_view_properties(view.properties)

        with ViewLayout(self._server, template_name=view_id) as vuetify_view:
            self._create_vuetify_ui(view_id, slicer_view)

        rca_view_adapter = RcaViewAdapter(
            view=slicer_view,
            name=view_id,
        )

        async def init_rca():
            # RCA protocol needs to be registered before the RCA adapter can be added to the server
            await self._server.ready
            self._server.controller.rc_area_register(rca_view_adapter)

        create_task(init_rca())
        return RcaView(vuetify_view, slicer_view, rca_view_adapter)

    def _create_vuetify_ui(self, view_id, slicer_view):
        with Div(
            style=(
                "flex: 1;"
                "display: grid;"
                "width: 100%;"
                "height: 100%;"
                "grid-template-columns: 20px auto;"
                "grid-template-rows: auto;"
                "z-index: 0;"
                "overflow: hidden;"
            )
        ):
            with Div(
                style="display: flex; flex-flow: column; background-color: transparent;"
            ):
                with VBtn(
                    size="medium",
                    variant="text",
                    classes="py-1",
                    click=self._get_reset_camera_f(slicer_view),
                ):
                    VIcon(
                        icon="mdi-camera-flip-outline",
                        size="medium",
                        color="white",
                    )
                    VTooltip(
                        "Reset Camera",
                        activator="parent",
                        location="right",
                        transition="slide-x-transition",
                    )

                self._fill_gutter(view_id, slicer_view)

            RemoteControlledArea(name=view_id, display="image")

    @abstractmethod
    def _get_reset_camera_f(self, slicer_view) -> Callable:
        pass

    @abstractmethod
    def _fill_gutter(self, view_id, slicer_view):
        pass


class RemoteThreeDViewFactory(RemoteViewFactory):
    def __init__(self, server: Server):
        super().__init__(server, ThreeDView, view_type=ViewType.THREE_D_VIEW)

    def _get_reset_camera_f(self, slicer_view: ThreeDView) -> Callable:
        return slicer_view.reset_camera

    def _fill_gutter(self, view_id, slicer_view):
        pass


class BlockSignals:
    def __init__(self):
        self._is_blocking = False

    def __enter__(self):
        self._is_blocking = True
        yield self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._is_blocking = False

    def __bool__(self):
        return self._is_blocking


class RemoteSliceViewFactory(RemoteViewFactory):
    def __init__(self, server: Server):
        super().__init__(server, SliceView, view_type=ViewType.SLICE_VIEW)

    def _get_reset_camera_f(self, slicer_view) -> Callable:
        return slicer_view.fit_slice_to_all

    def _fill_gutter(self, view_id, slicer_view):
        slider_value_state_id = f"slider_value_{view_id}"
        slider_min_state_id = f"slider_min_{view_id}"
        slider_max_state_id = f"slider_max_{view_id}"
        slider_step_state_id = f"slider_step_{view_id}"

        update_from_slicer = BlockSignals()
        update_from_trame = BlockSignals()

        @self._server.state.change(slider_value_state_id)
        def _on_view_slider_value_changed(*_, **kwargs):
            if update_from_slicer:
                return

            with update_from_trame:
                slicer_view.set_slice_value(kwargs[slider_value_state_id])
                slicer_view.schedule_render()

        def _on_slice_view_modified(view: SliceView):
            if update_from_trame:
                return

            with self._server.state as state, update_from_slicer:
                (
                    state[slider_min_state_id],
                    state[slider_max_state_id],
                ) = view.get_slice_range()
                state[slider_step_state_id] = view.get_slice_step()
                state[slider_value_state_id] = view.get_slice_value()

        slicer_view.add_modified_observer(_on_slice_view_modified)
        _on_slice_view_modified(slicer_view)

        """
        .v-slider.v-input--vertical>.v-input__control {
            min-height: 30px;
        }
        """

        VSlider(
            classes="slice-slider",
            direction="vertical",
            hide_details=True,
            theme="dark",
            v_model=(slider_value_state_id,),
            min=(slider_min_state_id,),
            max=(slider_max_state_id,),
            step=(slider_step_state_id,),
            dense=True,
        )
