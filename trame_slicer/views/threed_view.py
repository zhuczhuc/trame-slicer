import math
from enum import Enum
from typing import Optional

from slicer import (
    vtkMRMLAbstractViewNode,
    vtkMRMLApplicationLogic,
    vtkMRMLCameraDisplayableManager,
    vtkMRMLCameraNode,
    vtkMRMLCrosshairDisplayableManager,
    vtkMRMLCrosshairDisplayableManager3D,
    vtkMRMLCrosshairNode,
    vtkMRMLInteractionEventData,
    vtkMRMLMarkupsDisplayableManager,
    vtkMRMLModelDisplayableManager,
    vtkMRMLOrientationMarkerDisplayableManager,
    vtkMRMLRulerDisplayableManager,
    vtkMRMLScene,
    vtkMRMLSegmentationsDisplayableManager3D,
    vtkMRMLThreeDReformatDisplayableManager,
    vtkMRMLThreeDViewDisplayableManagerFactory,
    vtkMRMLTransformsDisplayableManager3D,
    vtkMRMLViewDisplayableManager,
    vtkMRMLViewLogic,
    vtkMRMLViewNode,
    vtkMRMLVolumeRenderingDisplayableManager,
)
from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkRenderingCore import vtkInteractorStyle3D, vtkRenderer
from vtkmodules.vtkRenderingVolume import vtkVolumePicker

from .abstract_view import AbstractView


class RenderView(AbstractView):
    """
    Copied and adapted from ctkVTKRenderView
    """

    def reset_focal_point(self):
        bounds = [0] * 6
        self.renderer().ComputeVisiblePropBounds(bounds)
        x_center = (bounds[1] + bounds[0]) / 2.0
        y_center = (bounds[3] + bounds[2]) / 2.0
        z_center = (bounds[5] + bounds[4]) / 2.0
        self.set_focal_point(x_center, y_center, z_center)

    def set_focal_point(self, x, y, z):
        if not self.renderer().IsActiveCameraCreated():
            return

        camera = self.renderer().GetActiveCamera()
        camera.SetFocalPoint(x, y, z)
        camera.ComputeViewPlaneNormal()
        camera.OrthogonalizeViewUp()
        self.renderer().ResetCameraClippingRange()
        self.renderer().UpdateLightsGeometryToFollowCamera()


class ViewDirection(Enum):
    LEFT = vtkMRMLCameraNode.Left
    RIGHT = vtkMRMLCameraNode.Right
    POSTERIOR = vtkMRMLCameraNode.Posterior
    ANTERIOR = vtkMRMLCameraNode.Anterior
    INFERIOR = vtkMRMLCameraNode.Inferior
    SUPERIOR = vtkMRMLCameraNode.Superior


class ThreeDView(RenderView):
    """
    Copied and adapted from qMRMLThreeDView
    """

    def __init__(
        self,
        scene: vtkMRMLScene,
        app_logic: vtkMRMLApplicationLogic,
        name: str,
        *args,
        **kwargs
    ):
        super().__init__(*args, **kwargs)

        factory = vtkMRMLThreeDViewDisplayableManagerFactory.GetInstance()
        factory.SetMRMLApplicationLogic(app_logic)

        managers = [
            vtkMRMLVolumeRenderingDisplayableManager.__name__,
            vtkMRMLCameraDisplayableManager.__name__,
            vtkMRMLViewDisplayableManager.__name__,
            vtkMRMLModelDisplayableManager.__name__,
            vtkMRMLThreeDReformatDisplayableManager.__name__,
            vtkMRMLCrosshairDisplayableManager3D.__name__,
            vtkMRMLOrientationMarkerDisplayableManager.__name__,
            vtkMRMLRulerDisplayableManager.__name__,
            vtkMRMLSegmentationsDisplayableManager3D.__name__,
            vtkMRMLMarkupsDisplayableManager.__name__,
            vtkMRMLTransformsDisplayableManager3D.__name__,
        ]

        for manager in managers:
            if not factory.IsDisplayableManagerRegistered(manager):
                factory.RegisterDisplayableManager(manager)

        self.displayable_manager_group.Initialize(factory, self.renderer())
        self.interactor().SetInteractorStyle(vtkInteractorStyle3D())

        # Use hardware picker in through vtkWorldPointPicker, this may be slightly slower
        # for generic cases, but way more efficient for some use cases (e.g. segmentation effects)
        # since we won't have to pick multiple times.
        self.renderer().SetSafeGetZ(True)
        self._quick_volume_picker = vtkVolumePicker()
        self._quick_volume_picker.SetPickFromList(True)  # will only pick volumes
        self._last_world_position = [0.0, 0.0, 0.0]
        self.name = name
        self.logic = vtkMRMLViewLogic()
        self.logic.SetMRMLApplicationLogic(app_logic)

        app_logic.GetViewLogics().AddItem(self.logic)
        self.set_mrml_scene(scene)

    def set_mrml_scene(self, scene: vtkMRMLScene) -> None:
        super().set_mrml_scene(scene)
        self.logic.SetMRMLScene(scene)
        if self.mrml_view_node is None:
            self.set_mrml_view_node(self.logic.AddViewNode(self.name))

    def reset_focal_point(self):
        saved_box_visible = True
        saved_axis_label_visible = True

        if self.mrml_view_node:
            # Save current visibility state of Box and AxisLabel
            saved_box_visible = self.mrml_view_node.GetBoxVisible()
            saved_axis_label_visible = self.mrml_view_node.GetAxisLabelsVisible()

            was_modifying = self.mrml_view_node.StartModify()
            # Hide Box and AxisLabel so they don't get taken into account when computing
            # the view boundaries
            self.mrml_view_node.SetBoxVisible(0)
            self.mrml_view_node.SetAxisLabelsVisible(0)
            self.mrml_view_node.EndModify(was_modifying)

        # Exclude crosshair from focal point computation
        crosshair_node = vtkMRMLCrosshairDisplayableManager().FindCrosshairNode(
            self.mrml_scene
        )
        crosshairMode = 0
        if crosshair_node:
            crosshairMode = crosshair_node.GetCrosshairMode()
            crosshair_node.SetCrosshairMode(vtkMRMLCrosshairNode.NoCrosshair)

        # Superclass resets the camera.
        super().reset_focal_point()

        if self.mrml_view_node:
            # Restore visibility state
            was_modifying = self.mrml_view_node.StartModify()
            self.mrml_view_node.SetBoxVisible(saved_box_visible)
            self.mrml_view_node.SetAxisLabelsVisible(saved_axis_label_visible)
            self.mrml_view_node.EndModify(was_modifying)
            # Inform the displayable manager that the view is reset, so it can
            # update the box/labels bounds.
            self.mrml_view_node.InvokeEvent(
                vtkMRMLViewNode.ResetFocalPointRequestedEvent
            )

        if crosshair_node:
            crosshair_node.SetCrosshairMode(crosshairMode)

        if self.renderer():
            self.renderer().ResetCameraClippingRange()

    def set_background_gradient_color(self, color1_rgb_int, color2_rgb_int):
        super().set_background_gradient_color(color1_rgb_int, color2_rgb_int)
        if not self.mrml_view_node:
            return

        self.mrml_view_node.SetBackgroundColor(*self._to_float_color(color1_rgb_int))
        self.mrml_view_node.SetBackgroundColor2(*self._to_float_color(color2_rgb_int))

    def set_box_visible(self, is_visible):
        if not self.mrml_view_node:
            return
        self.mrml_view_node.SetBoxVisible(is_visible)
        self.mrml_view_node.SetAxisLabelsVisible(is_visible)

    def rotate_to_view_direction(self, view_direction: ViewDirection) -> None:
        camera_node = self.get_camera_node()
        if not camera_node:
            return

        camera_node.RotateTo(view_direction.value)

    def get_camera_node(self) -> Optional[vtkMRMLCameraNode]:
        camera_dm = self.displayable_manager_group.GetDisplayableManagerByClassName(
            "vtkMRMLCameraDisplayableManager"
        )
        if not camera_dm:
            return None
        return camera_dm.GetCameraNode()

    def fit_view_to_content(self):
        with self.trigger_modified_once():
            self.reset_focal_point()
            self.reset_camera()
            self.rotate_to_view_direction(ViewDirection.ANTERIOR)

    def _reset_node_view_properties(self):
        super()._reset_node_view_properties()
        if not self.mrml_view_node:
            return

        self._call_if_value_not_none(
            self.set_box_visible, self._view_properties.box_visible
        )

    def set_ruler(
        self, ruler_type: Optional[int] = None, ruler_color: Optional[int] = None
    ):
        if ruler_type and ruler_type != vtkMRMLAbstractViewNode.RulerTypeNone:
            self.set_render_mode_to_orthographic()
        super().set_ruler(ruler_type, ruler_color)

    def set_render_mode_to_orthographic(self):
        self.mrml_view_node.SetRenderMode(1)

    def set_render_mode_to_perspective(self):
        self.mrml_view_node.SetRenderMode(0)

    def is_render_mode_perspective(self) -> bool:
        return self.mrml_view_node.GetRenderMode() == 0

    def zoom(self, factor):
        """
        Move the camera node closer / further from the focal point by a given factor.

        :param factor: Values between -inf and 1. Values greater than 0 will zoom in, below 0 will zoom out
        """
        if self.is_render_mode_perspective():
            self._zoom_camera_position(factor)
        else:
            self._zoom_parallel_scale(factor)

    def _zoom_parallel_scale(self, factor):
        camera_node = self.get_camera_node()

        parallel_factor = 1 - factor
        if parallel_factor <= 0:
            return

        camera_node.SetParallelScale(parallel_factor * camera_node.GetParallelScale())
        camera_node.ResetClippingRange()

    def _zoom_camera_position(self, factor):
        import numpy as np

        if factor >= 1:
            return

        camera_node = self.get_camera_node()
        camera_position = np.array(camera_node.GetPosition())
        focal_point = np.array(camera_node.GetFocalPoint())
        camera_node.SetPosition(
            camera_position + factor * (focal_point - camera_position)
        )
        camera_node.ResetClippingRange()

    def zoom_in(self):
        self.zoom(0.2)

    def zoom_out(self):
        self.zoom(-0.2)

    def process_event_data(self, ed: vtkMRMLInteractionEventData):
        if ed.GetType() == vtkCommand.MouseMoveEvent:
            position = self.interactor().GetEventPosition()
            hit, world_position = self._quick_pick(position, ed.GetRenderer())
            self._last_pick_hit = hit
            self._last_world_position = world_position

        # set "inaccurate" world position
        ed.SetWorldPosition(self._last_world_position, False)

    def has_last_quick_pick_hit(self) -> bool:
        return self._last_pick_hit

    def _quick_pick(
        self, display_position: tuple[int, int], poked_renderer: vtkRenderer
    ) -> tuple[bool, tuple[float, float, float]]:
        hit_surface, surface_position = ThreeDView._pick_world_point(
            display_position, poked_renderer
        )

        # _pick_world_point ignores volume-rendered images, do a volume picking, too.
        camera_node = self._camera_node()
        if camera_node is not None:
            # Set picklist to volume actors to restrict the volume picker to only pick volumes
            # (otherwise it would also perform cell picking on meshes, which can take a long time).
            pick_list = self._quick_volume_picker.GetPickList()
            pick_list.RemoveAllItems()
            props = poked_renderer.GetViewProps()
            props.InitTraversal()
            prop = props.GetNextProp()
            while prop is not None:
                prop.GetVolumes(pick_list)
                prop = props.GetNextProp()

            if pick_list.GetNumberOfItems() > 0:
                if self._quick_volume_picker.Pick(
                    display_position[0], display_position[1], 0, poked_renderer
                ):
                    volume_position = self._quick_volume_picker.GetPickPosition()
                    if not hit_surface:
                        return (True, volume_position)

                    camera_position = camera_node.GetPosition()
                    # Use QuickVolumePicker result instead of QuickPicker result if picked volume point
                    # is closer to the camera (or QuickPicker did not find anything).
                    surface_distance = math.dist(surface_position, camera_position)
                    volume_distance = math.dist(volume_position, camera_position)
                    if volume_distance < surface_distance:
                        return True, volume_position

        return hit_surface, surface_position

    @staticmethod
    def _pick_world_point(
        display_position: tuple[int, int], poked_renderer: vtkRenderer
    ) -> tuple[bool, tuple[float, float, float]]:
        # Unlike Slicer that uses a vtkWorldPointPicker directly, we copy most of its logic
        # to check if something has been picked.
        # This is useful for some interaction, since this remove the need for an additional
        # picker to check if we are interacting with something.
        # This assumes that GetZ() == 1.0 means nothing has been picked
        z = poked_renderer.GetZ(display_position[0], display_position[1])
        hit = True

        # if z is 1.0, we assume the user has picked a point on the
        # screen that has not been rendered into. Use the camera's focal
        # point for the z value.
        if z > 0.9999:
            hit = False
            # Get camera focal point and position. Convert to display (screen)
            # coordinates. We need a depth value for z-buffer.
            camera = poked_renderer.GetActiveCamera()
            focal_point = camera.GetFocalPoint()
            poked_renderer.SetWorldPoint(
                focal_point[0], focal_point[1], focal_point[2], 1.0
            )
            poked_renderer.WorldToDisplay()
            display_point = poked_renderer.GetDisplayPoint()
            z = display_point[2]

        # now convert the display point to world coordinates
        poked_renderer.SetDisplayPoint(
            float(display_position[0]), float(display_position[1]), z
        )
        poked_renderer.DisplayToWorld()
        world = poked_renderer.GetWorldPoint()
        world_point = (world[0] / world[3], world[1] / world[3], world[2] / world[3])

        return hit, world_point