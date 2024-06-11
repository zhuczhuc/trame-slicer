from vtkmodules.vtkCommonCore import vtkCommand
from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLViewNode
from vtkmodules.vtkMRMLDisplayableManager import (
    vtkMRMLCameraDisplayableManager, vtkMRMLViewDisplayableManager, vtkMRMLModelDisplayableManager,
    vtkMRMLThreeDReformatDisplayableManager, vtkMRMLCrosshairDisplayableManager3D,
    vtkMRMLOrientationMarkerDisplayableManager, vtkMRMLRulerDisplayableManager, vtkMRMLThreeDViewInteractorStyle,
    vtkMRMLCrosshairDisplayableManager
)
from vtkmodules.vtkMRMLLogic import vtkMRMLViewLogic
from vtkmodules.vtkRenderingCore import vtkInteractorStyle3D
from vtkmodules.vtkSlicerVolumeRenderingModuleMRMLDisplayableManager import vtkMRMLVolumeRenderingDisplayableManager

from .abstract_view import AbstractView
from .slicer_app import SlicerApp


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


class ThreeDView(RenderView):
    """
    Copied and adapted from qMRMLThreeDView
    """

    def __init__(self, app: SlicerApp, name: str):

        super().__init__()

        managers = [
            vtkMRMLVolumeRenderingDisplayableManager,
            vtkMRMLCameraDisplayableManager,
            vtkMRMLViewDisplayableManager,
            vtkMRMLModelDisplayableManager,
            vtkMRMLThreeDReformatDisplayableManager,
            vtkMRMLCrosshairDisplayableManager3D,
            vtkMRMLOrientationMarkerDisplayableManager,
            vtkMRMLRulerDisplayableManager,
        ]

        for manager in managers:
            manager = manager()
            manager.SetMRMLApplicationLogic(app.app_logic)
            self.displayable_manager_group.AddDisplayableManager(manager)

        self.displayable_manager_group.GetInteractor().Initialize()
        self.interactor_observer = vtkMRMLThreeDViewInteractorStyle()
        self.interactor_observer.SetDisplayableManagers(self.displayable_manager_group)
        self.interactor_observer.SetInteractor(self.interactor())
        self.interactor().SetInteractorStyle(vtkInteractorStyle3D())

        self.name = name
        self.logic = vtkMRMLViewLogic()
        self.logic.SetMRMLApplicationLogic(app.app_logic)

        app.app_logic.GetViewLogics().AddItem(self.logic)
        self.set_mrml_scene(app.scene)

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
        crosshair_node = vtkMRMLCrosshairDisplayableManager().FindCrosshairNode(self.mrml_scene)
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
            self.mrml_view_node.InvokeEvent(vtkMRMLViewNode.ResetFocalPointRequestedEvent)

        if crosshair_node:
            crosshair_node.SetCrosshairMode(crosshairMode)

        if self.renderer():
            self.renderer().ResetCameraClippingRange()
