from typing import TYPE_CHECKING

from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkMRMLDisplayableManager import vtkMRMLInteractionEventData
from vtkmodules.vtkRenderingCore import vtkRenderer
from vtkmodules.vtkRenderingVolume import vtkVolumePicker

if TYPE_CHECKING:
    from .threed_view import ThreeDView

import numpy as np

from .view_interaction_dispatch import ViewInteractionDispatch


class ThreedViewInteractionDispatch(ViewInteractionDispatch):
    def __init__(self, view: "ThreeDView"):
        super().__init__(view)

        # Use hardware picker in through vtkWorldPointPicker, this may be slightly slower
        # for generic cases, but way more efficient for some use cases (e.g. segmentation widget)
        # since we won't have to pick multiple times.
        self._quick_volume_picker = vtkVolumePicker()
        self._quick_volume_picker.SetPickFromList(True)  # will only pick volumes
        self._last_world_position = [0.0, 0.0, 0.0]
        self._last_pick_hit = None

    def process_event_data(self, event_data: vtkMRMLInteractionEventData):
        super().process_event_data(event_data)
        if event_data.GetType() == vtkCommand.MouseMoveEvent:
            position = self._view.interactor().GetEventPosition()
            hit, world_position = self._quick_pick(position, event_data.GetRenderer())
            self._last_pick_hit = hit
            self._last_world_position = world_position

        # set "inaccurate" world position
        event_data.SetWorldPosition(self._last_world_position, False)

    def has_pick_hit(self) -> bool:
        return bool(self._last_pick_hit)

    def _quick_pick(
        self, display_position: tuple[int, int], poked_renderer: vtkRenderer
    ) -> tuple[bool, tuple[float, float, float]]:
        hit_surface, surface_position = self._pick_world_point(
            display_position, poked_renderer
        )

        # _pick_world_point ignores volume-rendered images, do a volume picking, too.
        camera_node = self._view.get_camera_node()
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

            if pick_list.GetNumberOfItems() > 0 and self._quick_volume_picker.Pick(
                display_position[0], display_position[1], 0, poked_renderer
            ):
                volume_position = self._quick_volume_picker.GetPickPosition()
                if not hit_surface:
                    return True, volume_position

                camera_position = np.array(camera_node.GetPosition())
                # Use QuickVolumePicker result instead of QuickPicker result if picked volume point
                # is closer to the camera (or QuickPicker did not find anything).
                surface_distance = np.linalg.norm(
                    camera_position - np.array(surface_position)
                )
                volume_distance = np.linalg.norm(
                    camera_position - np.array(volume_position)
                )
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
