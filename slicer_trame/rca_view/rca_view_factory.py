from collections import defaultdict
from dataclasses import dataclass
from typing import Callable, Optional

from trame_client.widgets.html import Div
from trame_rca.widgets.rca import RemoteControlledArea
from trame_server import Server
from trame_server.utils.asynchronous import create_task
from trame_vuetify.widgets.vuetify3 import VBtn, VIcon, VSlider, VTooltip
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from slicer_trame.core import ViewManager
from slicer_trame.views import (
    AbstractView,
    AbstractViewChild,
    IViewFactory,
    SliceView,
    ThreeDView,
    ViewLayout,
    ViewLayoutDefinition,
    ViewType,
)

from .rca_render_scheduler import RcaEncoder
from .rca_view_adapter import RcaViewAdapter


@dataclass
class RcaView:
    vuetify_view: RemoteControlledArea
    slicer_view: AbstractViewChild
    view_adapter: RcaViewAdapter


def register_rca_factories(
    view_manager: ViewManager,
    server: Server,
    rca_encoder: RcaEncoder = RcaEncoder.JPEG,
    target_fps: float = 20.0,
    interactive_quality: int = 50,
) -> None:
    """
    Helper function to register all RCA factories to a view manager.
    """
    for f_type in [RemoteSliceViewFactory, RemoteThreeDViewFactory]:
        view_manager.register_factory(
            f_type(
                server,
                rca_encoder=rca_encoder,
                target_fps=target_fps,
                interactive_quality=interactive_quality,
            )
        )


class RemoteViewFactory(IViewFactory):
    def __init__(
        self,
        server: Server,
        view_ctor: Callable,
        view_type: ViewType,
        *,
        target_fps: Optional[float] = None,
        interactive_quality: Optional[int] = None,
        rca_encoder: Optional[RcaEncoder | str] = None,
    ):
        super().__init__()
        self._server = server
        self._view_ctor = view_ctor
        self._view_type = view_type

        self._target_fps = target_fps
        self._interactive_quality = interactive_quality
        self._rca_encoder = rca_encoder

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
            target_fps=self._target_fps,
            rca_encoder=self._rca_encoder,
            interactive_quality=self._interactive_quality,
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
                "position: relative;" "width: 100%;" "height: 100%;" "overflow: hidden;"
            )
        ):
            RemoteControlledArea(
                name=view_id,
                display="image",
                style="position: relative; width: 100%; height: 100%;",
                send_mouse_move=True,
            )

            with Div(
                classes="rca-slider-gutter",
                style="position: absolute;"
                "top: 0;"
                "left: 0;"
                "background-color: transparent;"
                "height: 100%;",
            ):
                with Div(
                    classes="rca-slider-gutter-content d-flex flex-column fill-height pa-2"
                ):
                    with VBtn(
                        size="medium",
                        variant="text",
                        click=slicer_view.reset_view,
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

    def _fill_gutter(self, view_id, slicer_view):
        pass


class RemoteThreeDViewFactory(RemoteViewFactory):
    def __init__(self, server: Server, **kwargs):
        super().__init__(server, ThreeDView, view_type=ViewType.THREE_D_VIEW, **kwargs)


class RemoteSliceViewFactory(RemoteViewFactory):
    def __init__(self, server: Server, **kwargs):
        super().__init__(server, SliceView, view_type=ViewType.SLICE_VIEW, **kwargs)
        self._is_updating_from_trame = defaultdict(bool)
        self._is_updating_from_slicer = defaultdict(bool)

    def _fill_gutter(self, view_id, slicer_view):
        slider_value_state_id = f"slider_value_{view_id}"
        slider_min_state_id = f"slider_min_{view_id}"
        slider_max_state_id = f"slider_max_{view_id}"
        slider_step_state_id = f"slider_step_{view_id}"

        @self._server.state.change(slider_value_state_id)
        def _on_view_slider_value_changed(*_, **kwargs):
            if self._is_updating_from_slicer[slider_value_state_id]:
                return

            self._is_updating_from_trame[slider_value_state_id] = True
            slicer_view.set_slice_value(kwargs[slider_value_state_id])
            self._is_updating_from_trame[slider_value_state_id] = False

        def _on_slice_view_modified(view: SliceView):
            if self._is_updating_from_trame[slider_value_state_id]:
                return

            self._is_updating_from_slicer[slider_value_state_id] = True
            with self._server.state as state:
                (
                    state[slider_min_state_id],
                    state[slider_max_state_id],
                ) = view.get_slice_range()
                state[slider_step_state_id] = view.get_slice_step()
                state[slider_value_state_id] = view.get_slice_value()
                state.flush()
            self._is_updating_from_slicer[slider_value_state_id] = False

        slicer_view.add_modified_observer(_on_slice_view_modified)
        _on_slice_view_modified(slicer_view)

        with VBtn(
            size="medium",
            variant="text",
            click=slicer_view.toggle_visible_in_3d,
        ):
            VIcon(
                icon="mdi-video-3d",
                size="medium",
                color="white",
            )
            VTooltip(
                "Show in 3D",
                activator="parent",
                location="right",
                transition="slide-x-transition",
            )

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
