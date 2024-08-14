from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass

from trame_rca.widgets.rca import RemoteControlledArea
from trame_server import Server
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkMRMLLogic import vtkMRMLApplicationLogic

from slicer_trame.components.layout_grid import SlicerView, SlicerViewType
from slicer_trame.components.rca_view_adapter import ViewAdapter
from slicer_trame.components.view_layout import ViewLayout
from slicer_trame.slicer import ThreeDView, AsyncIORendering, AbstractView


class IViewFactory(ABC):
    """
    Interface for view factories.
    """

    @abstractmethod
    def can_create_view(self, view_type: SlicerView) -> bool:
        pass

    @abstractmethod
    def create_view(
        self,
        view_type: SlicerView,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ):
        pass


class RemoteViewFactory(IViewFactory):
    @dataclass
    class View:
        rca: RemoteControlledArea
        slicer_view: AbstractView
        view_adapter: ViewAdapter

    def __init__(self, server: Server, view_ctor: Callable, view_type: SlicerViewType):
        super().__init__()
        self._server = server
        self._view_ctor = view_ctor
        self._view_type = view_type

    def can_create_view(self, view_type: SlicerViewType) -> bool:
        return view_type == self._view_type

    def create_view(
        self,
        view_type: SlicerView,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
    ):
        slicer_view = self._view_ctor(
            scene=scene,
            app_logic=app_logic,
            name=view_type.singleton_tag,
            scheduled_render_strategy=AsyncIORendering(),
        )

        if view_type.properties.group:
            slicer_view.set_view_group(view_type.properties.group)

        with ViewLayout(self._server, template_name=view_type.singleton_tag):
            rca = RemoteControlledArea(name=view_type, display="image")

        view_adapter = ViewAdapter(
            window=slicer_view.render_window(),
            name=view_type.singleton_tag,
        )

        def init_rca():
            self._server.controller.rc_area_register(view_adapter)

        if self._server.ready:
            init_rca()
        else:
            self._server.controller.on_server_ready.add(init_rca)

        return self.View(rca, slicer_view, view_adapter)


class RemoteThreeDViewFactory(RemoteViewFactory):
    def __init__(self, server: Server):
        super().__init__(server, ThreeDView, view_type=SlicerViewType.THREE_D_VIEW)


class RemoteSliceViewFactory(RemoteViewFactory):
    def __init__(self, server: Server):
        super().__init__(server, SlicerView, view_type=SlicerViewType.SLICE_VIEW)
