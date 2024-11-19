from enum import IntEnum
from typing import Callable, Optional

from vtkmodules.vtkCommonCore import vtkCommand, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData, vtkQuad
from vtkmodules.vtkInteractionWidgets import (
    vtkContourWidget,
    vtkFocalPlanePointPlacer,
    vtkLinearContourLineInterpolator,
    vtkOrientedGlyphContourRepresentation,
)
from vtkmodules.vtkMRMLDisplayableManager import vtkMRMLInteractionEventData
from vtkmodules.vtkRenderingCore import vtkCoordinate, vtkRenderWindow

from trame_slicer.views import AbstractView, AbstractViewInteractor

from .segmentation_editor import SegmentationEditor
from .segmentation_effect import SegmentationEffect


class ScissorShape(IntEnum):
    Polygon = 0


class ScissorMode(IntEnum):
    Inside = 0
    Outside = 1


class ScissorPolygonBrush:
    """Use a vtkContourWidget to display the scissor"""

    def __init__(self, render_window: vtkRenderWindow) -> None:
        self._contour_widget = vtkContourWidget()
        self._contour_widget.SetInteractor(render_window.GetInteractor())

        self._contour_repr = vtkOrientedGlyphContourRepresentation()
        self._contour_repr.GetLinesProperty().SetColor(1.0, 1.0, 0.0)
        self._contour_repr.AlwaysOnTopOn()

        self._inter = vtkLinearContourLineInterpolator()
        self._contour_repr.SetLineInterpolator(self._inter)
        self._point_placer = vtkFocalPlanePointPlacer()
        self._contour_repr.SetPointPlacer(self._point_placer)

    @property
    def widget(self) -> vtkContourWidget:
        return self._contour_widget

    @property
    def representation(self) -> vtkOrientedGlyphContourRepresentation:
        return self._contour_repr


# On slice view project 2D points on slice (world pos)
# On 3D view project 2D points on focal plane (world pos)


class SegmentScissorEffect3D(SegmentationEffect):
    def __init__(self, view: AbstractView, editor: SegmentationEditor) -> None:
        super().__init__(editor)
        self._view = view
        self._shape = ScissorShape.Polygon
        self._mode = ScissorMode.Inside
        self._brush = ScissorPolygonBrush(view.render_window())
        self._brush.widget.AddObserver(
            vtkCommand.EndInteractionEvent, self._end_interaction, 1.0
        )
        self._brush_enabled = False

    def enable_brush(self) -> None:
        self._brush_enabled = True
        # self._brush.widget.GetEventTranslator().SetTranslation(vtkCommand.MouseMoveEvent, vtkWidgetEvent.NoEvent)

    def disable_brush(self) -> None:
        self._brush_enabled = False
        if self._brush.representation.GetNumberOfNodes() > 0:
            self.commit()
        self._brush.widget.Off()

    def is_brush_enabled(self) -> bool:
        return self._brush_enabled

    def commit(self):
        # DisplayToWorldCoordinate
        dc_to_wc = vtkCoordinate()
        dc_to_wc.SetCoordinateSystemToDisplay()
        representation = self._brush.representation
        renderer = self._view.renderer()

        polydata = vtkPolyData()

        point_count = representation.GetNumberOfNodes()
        points = vtkPoints()
        polydata.SetPoints(points)
        points.SetNumberOfPoints(2 * point_count)

        cells = vtkCellArray()
        polydata.SetPolys(cells)

        for i in range(point_count):
            node_position_dc = [0.0, 0.0]
            representation.GetNthNodeDisplayPosition(i, node_position_dc)

            # Compute near/far origin
            dc_to_wc.SetValue(node_position_dc[0], node_position_dc[1], 0.0)
            wc = dc_to_wc.GetComputedWorldValue(renderer)
            node_position_near = (wc[0], wc[1], wc[2])

            dc_to_wc.SetValue(node_position_dc[0], node_position_dc[1], 1.0)
            wc = dc_to_wc.GetComputedWorldValue(renderer)
            node_position_far = (wc[0], wc[1], wc[2])

            points.SetPoint(2 * i, node_position_near)
            points.SetPoint(2 * i + 1, node_position_far)

            quad = vtkQuad()
            quad.GetPointIds().SetNumberOfIds(4)
            quad.GetPointIds().SetId(0, 2 * i)
            quad.GetPointIds().SetId(1, 2 * i + 1)
            quad.GetPointIds().SetId(2, (2 * i + 3) % (2 * point_count))
            quad.GetPointIds().SetId(3, (2 * i + 2) % (2 * point_count))
            cells.InsertNextCell(quad)

        self._editor.apply_poly(polydata)

        representation.ClearAllNodes()
        # Reset widget state so next left click will place the first point
        self._brush.widget.SetWidgetState(vtkContourWidget.Start)

        self.editor.update_surface_representation()

    def _end_interaction(self, obj, ev):
        self.commit()


class SegmentScissorEffect2D(SegmentationEffect):
    pass


class SegmentScissorEffect3DInteractor(AbstractViewInteractor):
    def __init__(self, effect: SegmentScissorEffect3D) -> None:
        super().__init__()
        self.effect = effect  # for type hints
        self._render_callback: Optional[Callable] = None
        # Event we may consume and how we consume them
        self._supported_events = {
            int(vtkCommand.MouseMoveEvent): self.mouse_moved,
            int(vtkCommand.LeftButtonPressEvent): self.left_pressed,
        }

    @property
    def render_callback(self) -> Optional[Callable]:
        return self._render_callback

    @render_callback.setter
    def render_callback(self, callback: Optional[Callable]) -> None:
        self._render_callback = callback

    def trigger_render_callback(self) -> None:
        if self._render_callback:
            self._render_callback()

    def process_event(self, event_data: vtkMRMLInteractionEventData) -> bool:
        if event_data.GetType() not in self._supported_events:
            return False

        callback = self._supported_events.get(event_data.GetType())
        return callback(event_data) if callback is not None else False

    def left_pressed(self, event_data: vtkMRMLInteractionEventData) -> bool:
        if self.effect.is_brush_enabled():
            self.trigger_render_callback()
            self.effect._brush.widget.SetWidgetState(vtkContourWidget.Start)
            self.effect._brush.widget.SetDefaultRenderer(event_data.GetRenderer())
            self.effect._brush.widget.SetCurrentRenderer(event_data.GetRenderer())
            self.effect._brush.representation.SetRenderer(event_data.GetRenderer())
            self.effect._brush.widget.SetRepresentation(
                self.effect._brush.representation
            )
            self.effect._brush.representation.ClearAllNodes()
            self.effect._brush.widget.On()
            self.effect._brush.widget.ContinuousDrawOn()
            self.effect._brush.widget.FollowCursorOn()
            self.effect._brush.representation.ClosedLoopOn()
            x, y = event_data.GetDisplayPosition()
            self.effect._brush.representation.AddNodeAtDisplayPosition(x, y)
            self.effect._brush.widget.SetWidgetState(vtkContourWidget.Define)
            print("TAMERE", flush=True)
            print(f"ce connard de widget {self.effect._brush.widget}")
            print(
                f"cette grosse chienne de representation {self.effect._brush.representation}"
            )
            self.effect._view.render_window().Render()
            return False
            # self.effect._brush.widget.GetEventTranslator().InvokeEvent(vtkCommand.MouseMoveEvent)

        return False  # Always let other interactors and displayable managers do whatever they want

    def mouse_moved(self, event_data: vtkMRMLInteractionEventData) -> bool:
        if self.effect.is_brush_enabled():
            # self.effect._brush.widget.SetCurrentRenderer(event_data.GetRenderer())
            self.trigger_render_callback()

        return False  # Always let other interactors and displayable managers do whatever they want
