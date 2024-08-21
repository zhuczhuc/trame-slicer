from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from trame_client.widgets.html import Div
from trame_rca.widgets.rca import RemoteControlledArea
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from trame_vuetify.widgets.vuetify3 import VBtn, VIcon, VSlider, VTooltip
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from slicer_trame.components.layout_grid import SlicerView, SlicerViewType
from slicer_trame.components.rca_view_adapter import RcaViewAdapter
from slicer_trame.components.view_layout import ViewLayout
from slicer_trame.slicer.abstract_view import AbstractView
from slicer_trame.slicer.slice_view import SliceView
from slicer_trame.slicer.threed_view import ThreeDView


class IViewFactory(ABC):
    """
    Interface for view factories.
    """

    @abstractmethod
    def can_create_view(self, view: SlicerView) -> bool:
        pass

    @abstractmethod
    def create_view(
        self,
        view: SlicerView,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ):
        pass


@dataclass
class RcaView:
    vuetify_view: RemoteControlledArea
    slicer_view: type[AbstractView]
    view_adapter: RcaViewAdapter


class RemoteViewFactory(IViewFactory):
    def __init__(self, server: Server, view_ctor: Callable, view_type: SlicerViewType):
        super().__init__()
        self._server = server
        self._view_ctor = view_ctor
        self._view_type = view_type

    def can_create_view(self, view: SlicerView) -> bool:
        return view.type == self._view_type

    def create_view(
        self,
        view: SlicerView,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ):
        view_id = view.singleton_tag
        slicer_view: AbstractView = self._view_ctor(
            scene=scene,
            app_logic=app_logic,
            name=view_id,
        )

        if view.properties.group:
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
        RemoteControlledArea(name=view_id, display="image")


class RemoteThreeDViewFactory(RemoteViewFactory):
    def __init__(self, server: Server):
        super().__init__(server, ThreeDView, view_type=SlicerViewType.THREE_D_VIEW)


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
        super().__init__(server, SliceView, view_type=SlicerViewType.SLICE_VIEW)

    def _create_vuetify_ui(self, view_id, slicer_view: SliceView):
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
                style="display: flex; flex-flow: column; background-color: black;"
            ):
                with VBtn(
                    size="medium",
                    variant="text",
                    classes="py-1",
                    click=slicer_view.fit_slice_to_all,
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

                VSlider(
                    direction="vertical",
                    hide_details="true",
                    theme="dark",
                    v_model=(slider_value_state_id,),
                    min=(slider_min_state_id,),
                    max=(slider_max_state_id,),
                    step=(slider_step_state_id,),
                )
            RemoteControlledArea(name=view_id, display="image")
