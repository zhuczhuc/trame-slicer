from contextlib import contextmanager
from dataclasses import dataclass
from sys import float_info
from typing import Callable, List, Literal, Optional, TypeVar, Union

from slicer import (
    vtkMRMLAbstractDisplayableManager,
    vtkMRMLAbstractViewNode,
    vtkMRMLDisplayableManagerGroup,
    vtkMRMLInteractionEventData,
    vtkMRMLScene,
    vtkMRMLViewNode,
)
from vtkmodules import vtkRenderingCore
from vtkmodules.vtkCommonCore import reference as vtkref
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import (
    vtkInteractorStyle,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from trame_slicer.utils import VtkEventDispatcher

from .abstract_view_interactor import AbstractViewInteractor
from .render_scheduler import DirectRendering, ScheduledRenderStrategy

ViewOrientation = Literal["Axial", "Coronal", "Sagittal"]


@dataclass
class ViewProps:
    label: Optional[str] = None
    orientation: Optional[ViewOrientation] = None
    color: Optional[str] = None
    group: Optional[int] = None
    background_color: Optional[Union[str, tuple[str, str]]] = None
    box_visible: Optional[bool] = None

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
            "background_color": "background_color",
            "box_visible": "box_visible",
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
        self._render_window.ShowWindowOff()
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

        self._user_interactors: list[AbstractViewInteractor] = []
        self._focused_displayable_manager: Optional[
            vtkMRMLAbstractDisplayableManager
        ] = None

        self._add_observers()

    def add_user_interactor(self, observer: AbstractViewInteractor):
        self._user_interactors.append(observer)

    def remove_user_interactor(self, observer: AbstractViewInteractor):
        self._user_interactors.remove(observer)

    def _add_observers(self):
        iren = self.interactor()

        commands = [
            vtkCommand.MouseMoveEvent,
            vtkCommand.RightButtonDoubleClickEvent,
            vtkCommand.RightButtonPressEvent,
            vtkCommand.RightButtonReleaseEvent,
            vtkCommand.MiddleButtonDoubleClickEvent,
            vtkCommand.MiddleButtonPressEvent,
            vtkCommand.MiddleButtonReleaseEvent,
            vtkCommand.LeftButtonDoubleClickEvent,
            vtkCommand.LeftButtonPressEvent,
            vtkCommand.LeftButtonReleaseEvent,
            vtkCommand.EnterEvent,
            vtkCommand.LeaveEvent,
            vtkCommand.MouseWheelForwardEvent,
            vtkCommand.MouseWheelBackwardEvent,
            vtkCommand.StartPinchEvent,
            vtkCommand.PinchEvent,
            vtkCommand.EndPinchEvent,
            vtkCommand.StartRotateEvent,
            vtkCommand.RotateEvent,
            vtkCommand.EndRotateEvent,
            vtkCommand.StartPanEvent,
            vtkCommand.PanEvent,
            vtkCommand.EndPanEvent,
            vtkCommand.TapEvent,
            vtkCommand.LongTapEvent,
            vtkCommand.KeyPressEvent,
            vtkCommand.KeyReleaseEvent,
            vtkCommand.CharEvent,
            vtkCommand.ExposeEvent,
            vtkCommand.ConfigureEvent,
        ]

        for command in commands:
            iren.AddObserver(command, self._event_delegate, 0.0)

    def _event_delegate(self, caller, ev):
        event_id = vtkCommand.GetEventIdFromString(ev)

        position = self.interactor().GetEventPosition()
        poked_renderer = self.interactor().FindPokedRenderer(position[0], position[1])
        if not poked_renderer:
            return

        origin = poked_renderer.GetOrigin()

        # Fill basic information
        ed = vtkMRMLInteractionEventData()
        ed.SetType(event_id)
        ed.SetDisplayPosition([position[0] - origin[0], position[1] - origin[1]])
        ed.SetMouseMovedSinceButtonDown(True)
        ed.SetAttributesFromInteractor(self.interactor())
        ed.SetRenderer(poked_renderer)

        # Let subclasses add information to event data
        self.process_event_data(ed)

        # Then let user interactors process it. They can abort event processing earlier.
        for interactor in self._user_interactors:
            if interactor.process_event(ed):
                return

        processed = self._delegate_interaction_event_data_to_displayable_managers(ed)
        iren_state = self.interactor().GetInteractorStyle().GetState()
        if not processed or iren_state != vtkRenderingCore.VTKIS_NONE:
            self._process_events(event_id)

    def process_event_data(self, ed: vtkMRMLInteractionEventData):
        pass  # default implementation does nothing

    def _delegate_interaction_event_data_to_displayable_managers(
        self, event_data: vtkMRMLInteractionEventData
    ):
        manager_count = self.displayable_manager_group.GetDisplayableManagerCount()
        if manager_count == 0:
            return

        # Invalidate display position if 3D event
        if event_data.GetType() in [vtkCommand.Button3DEvent, vtkCommand.Move3DEvent]:
            event_data.SetDisplayPositionInvalid()

        # Find the most suitable displayable manager
        closest_distance = float_info.max
        closest_displayable_manager: Optional[vtkMRMLAbstractDisplayableManager] = None
        for i in range(manager_count):
            manager = self.displayable_manager_group.GetNthDisplayableManager(i)
            if manager is None:
                continue
            distance = vtkref(float_info.max)
            if manager.CanProcessInteractionEvent(event_data, distance):  # noqa
                if not closest_displayable_manager or distance < closest_distance:  # noqa
                    closest_displayable_manager = manager
                    closest_distance = distance

        if not closest_displayable_manager:
            # None of the displayable managers can process the event, just ignore it
            return False

        # Notify displayable managers about focus change
        old_focus = self._focused_displayable_manager
        if old_focus != closest_displayable_manager:
            if old_focus is not None:
                closest_displayable_manager.SetHasFocus(False, event_data)
            self._focused_displayable_manager = closest_displayable_manager
            if closest_displayable_manager is not None:
                closest_displayable_manager.SetHasFocus(True, event_data)

        # Process event with new displayable manager
        if self._focused_displayable_manager is None:
            return False

        # This prevents desynchronized update of displayable managers during user interaction
        # (ie. slice intersection widget or segmentations lagging behind during slice translation)
        app_logic = self._focused_displayable_manager.GetMRMLApplicationLogic()
        if app_logic is not None:
            self._focused_displayable_manager.GetMRMLApplicationLogic().PauseRender()

        processed = self._focused_displayable_manager.ProcessInteractionEvent(
            event_data
        )

        # Restore rendering
        if app_logic is not None:
            self._focused_displayable_manager.GetMRMLApplicationLogic().ResumeRender()

        return processed

    def _process_events(self, event_id):
        style = self.interactor_style()
        if not style:
            return

        jump_table = {
            int(vtkCommand.MouseMoveEvent): style.OnMouseMove,
            int(vtkCommand.RightButtonDoubleClickEvent): style.OnRightButtonDoubleClick,
            int(vtkCommand.RightButtonPressEvent): style.OnRightButtonDown,
            int(vtkCommand.RightButtonReleaseEvent): style.OnRightButtonUp,
            int(
                vtkCommand.MiddleButtonDoubleClickEvent
            ): style.OnMiddleButtonDoubleClick,
            int(vtkCommand.MiddleButtonPressEvent): style.OnMiddleButtonDown,
            int(vtkCommand.MiddleButtonReleaseEvent): style.OnMiddleButtonUp,
            int(vtkCommand.LeftButtonDoubleClickEvent): style.OnLeftButtonDoubleClick,
            int(vtkCommand.LeftButtonPressEvent): style.OnLeftButtonDown,
            int(vtkCommand.LeftButtonReleaseEvent): style.OnLeftButtonUp,
            int(vtkCommand.EnterEvent): style.OnEnter,
            int(vtkCommand.LeaveEvent): style.OnLeave,
            int(vtkCommand.MouseWheelForwardEvent): style.OnMouseWheelForward,
            int(vtkCommand.MouseWheelBackwardEvent): style.OnMouseWheelBackward,
            int(vtkCommand.StartPinchEvent): style.OnStartPinch,
            int(vtkCommand.PinchEvent): style.OnPinch,
            int(vtkCommand.EndPinchEvent): style.OnEndPinch,
            int(vtkCommand.StartRotateEvent): style.OnStartRotate,
            int(vtkCommand.RotateEvent): style.OnRotate,
            int(vtkCommand.EndRotateEvent): style.OnEndRotate,
            int(vtkCommand.StartPanEvent): style.OnStartPan,
            int(vtkCommand.PanEvent): style.OnPan,
            int(vtkCommand.EndPanEvent): style.OnEndPan,
            int(vtkCommand.TapEvent): style.OnTap,
            int(vtkCommand.LongTapEvent): style.OnLongTap,
            int(vtkCommand.KeyPressEvent): style.OnConfigure,
            int(vtkCommand.KeyReleaseEvent): style.OnKeyRelease,
            int(vtkCommand.CharEvent): style.OnChar,
            int(vtkCommand.ExposeEvent): style.OnExpose,
            int(vtkCommand.ConfigureEvent): style.OnConfigure,
        }

        if event_id in jump_table:
            jump_table[event_id]()

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
        self._render_window_interactor.Render()
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

        with self.trigger_modified_once():
            self._modified_dispatcher.detach_vtk_observer(self._mrml_node_obs_id)
            self.mrml_view_node = node
            self.displayable_manager_group.SetMRMLDisplayableNode(node)
            self._reset_node_view_properties()
            self._mrml_node_obs_id = self._modified_dispatcher.attach_vtk_observer(
                node, "ModifiedEvent"
            )

    def set_view_properties(self, view_properties: ViewProps):
        self._view_properties = view_properties
        self._reset_node_view_properties()

    def _reset_node_view_properties(self):
        if not self.mrml_view_node:
            return

        with self.trigger_modified_once():
            self._call_if_value_not_none(
                self.mrml_view_node.SetViewGroup, self._view_properties.group
            )
            self._call_if_value_not_none(
                self.set_background_color_from_string,
                self._view_properties.background_color,
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

    def fit_view_to_content(self):
        self.reset_camera()

    def reset_view(self):
        with self.trigger_modified_once():
            self._reset_node_view_properties()
            self.fit_view_to_content()
            self.schedule_render()
            self._trigger_modified()

    def set_background_color(self, rgb_int_color: list[int]) -> None:
        self.set_background_gradient_color(rgb_int_color, rgb_int_color)

    def set_background_gradient_color(
        self, color1_rgb_int: list[int], color2_rgb_int: list[int]
    ) -> None:
        self.first_renderer().SetBackground(*self._to_float_color(color1_rgb_int))
        self.first_renderer().SetBackground2(*self._to_float_color(color2_rgb_int))

    def set_background_color_from_string(self, color: Union[str, tuple[str, str]]):
        if isinstance(color, str):
            c1 = c2 = color
        else:
            c1, c2 = color
        self.set_background_gradient_color(
            self._str_to_color(c1), (self._str_to_color(c2))
        )

    @staticmethod
    def _to_float_color(rgb_int_color: list[int]) -> list[float]:
        return [int_color / 255.0 for int_color in rgb_int_color]

    @classmethod
    def _str_to_color(cls, color: str) -> list[int]:
        from webcolors import hex_to_rgb, name_to_rgb

        try:
            int_color = hex_to_rgb(color)
        except ValueError:
            int_color = name_to_rgb(color)
        return [int_color.red, int_color.green, int_color.blue]

    def _trigger_modified(self) -> None:
        self._modified_dispatcher.trigger_dispatch()

    @contextmanager
    def trigger_modified_once(self):
        prev_blocked = self._modified_dispatcher.is_blocked()
        self._modified_dispatcher.set_blocked(True)
        try:
            yield
        finally:
            self._modified_dispatcher.set_blocked(prev_blocked)
            self._trigger_modified()

    def set_orientation_marker(
        self,
        orientation_marker: Optional[int] = None,
        orientation_marker_size: Optional[int] = None,
    ):
        """
        Sets the orientation marker and size.
        Orientation Enums are defined in the vtkMRMLAbstractViewNode class.
        """
        if orientation_marker is not None:
            self.mrml_view_node.SetOrientationMarkerType(orientation_marker)

        if orientation_marker_size is not None:
            self.mrml_view_node.SetOrientationMarkerSize(orientation_marker_size)

    def set_ruler(
        self, ruler_type: Optional[int] = None, ruler_color: Optional[int] = None
    ):
        """
        Sets the ruler type and color.
        Ruler Enums are defined in the vtkMRMLAbstractViewNode class.
        """
        if ruler_type is not None:
            self.mrml_view_node.SetRulerType(ruler_type)

        if ruler_color is not None:
            self.mrml_view_node.SetRulerColor(ruler_color)

    def start_interactor(self) -> None:
        self.interactor().Start()
