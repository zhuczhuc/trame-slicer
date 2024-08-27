from dataclasses import dataclass
from typing import Callable, List, Literal, Optional, TypeVar

from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkMRMLCore import (
    vtkMRMLAbstractViewNode,
    vtkMRMLScene,
    vtkMRMLViewNode,
)
from vtkmodules.vtkMRMLDisplayableManager import vtkMRMLDisplayableManagerGroup
from vtkmodules.vtkRenderingCore import (
    vtkInteractorStyle,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from .render_scheduler import DirectRendering, ScheduledRenderStrategy
from .vtk_event_dispatcher import VtkEventDispatcher

ViewOrientation = Literal["Axial", "Coronal", "Sagittal"]


@dataclass
class ViewProps:
    label: Optional[str] = None
    orientation: Optional[ViewOrientation] = None
    color: Optional[str] = None
    group: Optional[int] = None

    def __post_init__(self):
        if self.group is not None:
            self.group = int(self.group)

    def to_xml(self) -> str:
        property_map = {
            key: getattr(self, value) for key, value in self.xml_name_map().items()
        }

        return "".join(
            f'<property name="{name}" action="default">{value}</property>'
            for name, value in property_map.items()
            if value is not None
        )

    @classmethod
    def xml_name_map(cls):
        return {
            "orientation": "orientation",
            "viewlabel": "label",
            "viewcolor": "color",
            "viewgroup": "group",
        }

    @classmethod
    def from_xml_dict(cls, xml_prop_dict: dict):
        name_map = cls.xml_name_map()
        renamed_dict = {name_map[key]: value for key, value in xml_prop_dict.items()}
        return cls(**renamed_dict)


AbstractViewChild = TypeVar("AbstractViewChild", bound="AbstractView")


class AbstractView:
    """
    Simple container class for a VTK Render Window, Renderers and VTK MRML Displayable Manager Group
    """

    def __init__(
        self,
        scheduled_render_strategy: Optional[ScheduledRenderStrategy] = None,
        *args,
        **kwargs,
    ):
        self._renderer = vtkRenderer()
        self._render_window = vtkRenderWindow()
        self._render_window.SetMultiSamples(0)
        self._render_window.AddRenderer(self._renderer)

        self._render_window_interactor = vtkRenderWindowInteractor()
        self._render_window_interactor.SetRenderWindow(self._render_window)

        self.displayable_manager_group = vtkMRMLDisplayableManagerGroup()
        self.displayable_manager_group.SetRenderer(self._renderer)
        self.displayable_manager_group.AddObserver(
            vtkCommand.UpdateEvent, self.schedule_render
        )
        self.mrml_scene: Optional[vtkMRMLScene] = None
        self.mrml_view_node: Optional[vtkMRMLAbstractViewNode] = None

        self._scheduled_render: Optional[ScheduledRenderStrategy] = None
        self.set_scheduled_render(scheduled_render_strategy or DirectRendering())
        self._view_properties = ViewProps()

        self._modified_dispatcher = VtkEventDispatcher()
        self._modified_dispatcher.set_dispatch_information(self)
        self._mrml_node_obs_id = None

    def set_scheduled_render(
        self, scheduled_render_strategy: ScheduledRenderStrategy
    ) -> None:
        self._scheduled_render = scheduled_render_strategy or DirectRendering()
        self._scheduled_render.set_abstract_view(self)

    def finalize(self):
        self.render_window().ShowWindowOff()
        self.render_window().Finalize()

    def add_renderer(self, renderer: vtkRenderer) -> None:
        self._render_window.AddRenderer(renderer)

    def renderers(self) -> List[vtkRenderer]:
        return list(self._render_window.GetRenderers())

    def first_renderer(self) -> vtkRenderer:
        return self._renderer

    def renderer(self) -> vtkRenderer:
        return self.first_renderer()

    def schedule_render(self, *_) -> None:
        if not self._scheduled_render:
            return
        self._scheduled_render.schedule_render()

    def render(self) -> None:
        self._render_window.Render()
        if not self._scheduled_render:
            return
        self._scheduled_render.did_render()

    def render_window(self) -> vtkRenderWindow:
        return self._render_window

    def interactor(self) -> vtkRenderWindowInteractor:
        return self.render_window().GetInteractor()

    def interactor_style(self) -> Optional[vtkInteractorStyle]:
        return self.interactor().GetInteractorStyle()

    def set_mrml_view_node(self, node: vtkMRMLViewNode) -> None:
        if self.mrml_view_node == node:
            return

        self._modified_dispatcher.detach_vtk_observer(self._mrml_node_obs_id)
        self.mrml_view_node = node
        self.displayable_manager_group.SetMRMLDisplayableNode(node)
        self._refresh_node_view_properties()
        self._mrml_node_obs_id = self._modified_dispatcher.attach_vtk_observer(
            node, "ModifiedEvent"
        )

    def set_view_properties(self, view_properties: ViewProps):
        self._view_properties = view_properties
        self._refresh_node_view_properties()

    def _refresh_node_view_properties(self):
        if not self.mrml_view_node:
            return

        self._call_if_value_not_none(
            self.mrml_view_node.SetViewGroup, self._view_properties.group
        )

    def get_view_group(self) -> int:
        if not self.mrml_view_node:
            return 0
        return self.mrml_view_node.GetViewGroup()

    @classmethod
    def _call_if_value_not_none(cls, setter, value):
        if value is not None:
            setter(value)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        if self.mrml_scene == scene:
            return

        self.mrml_scene = scene
        if self.mrml_view_node and self.mrml_view_node.GetScene() != scene:
            self.mrml_view_node = None

    def reset_camera(self):
        for renderer in self._render_window.GetRenderers():
            renderer.ResetCamera()

    def add_modified_observer(self, observer: Callable) -> None:
        self._modified_dispatcher.add_dispatch_observer(observer)

    def remove_modified_observer(self, observer: Callable) -> None:
        self._modified_dispatcher.remove_dispatch_observer(observer)

    def get_view_node_id(self) -> str:
        return self.mrml_view_node.GetID() if self.mrml_view_node else ""
