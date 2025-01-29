from pathlib import Path
from typing import Optional

import vtk
from vtkmodules.vtkCommonCore import vtkCollection, vtkOutputWindow
from vtkmodules.vtkMRMLCore import vtkMRMLCrosshairNode, vtkMRMLScene, vtkMRMLSliceNode
from vtkmodules.vtkMRMLDisplayableManager import (
    vtkMRMLSliceViewDisplayableManagerFactory,
    vtkMRMLThreeDViewDisplayableManagerFactory,
)
from vtkmodules.vtkMRMLLogic import vtkMRMLColorLogic
from vtkmodules.vtkSlicerBaseLogic import vtkSlicerApplicationLogic
from vtkmodules.vtkSlicerMarkupsModuleLogic import vtkSlicerMarkupsLogic
from vtkmodules.vtkSlicerSubjectHierarchyModuleLogic import (
    vtkSlicerSubjectHierarchyModuleLogic,
)
from vtkmodules.vtkSlicerTerminologiesModuleLogic import (
    vtkSlicerTerminologiesModuleLogic,
)
from vtkmodules.vtkSlicerVolumesModuleLogic import vtkSlicerVolumesLogic

from .display_manager import DisplayManager
from .io_manager import IOManager
from .view_manager import ViewManager
from .volume_rendering import VolumeRendering


class SlicerApp:
    """
    Container for the core components of a Slicer application.
    Instantiates the scene, application logic and layout manager.
    Configures the default nodes present in the scene.
    """

    def __init__(self, share_directory: Optional[str] = None):
        from slicer_trame.resources import resources_path

        self.share_directory = Path(share_directory or resources_path())

        # Output VTK warnings to console by default
        vtk_out = vtkOutputWindow()
        vtk_out.SetDisplayModeToAlwaysStdErr()
        vtkOutputWindow.SetInstance(vtk_out)

        self.scene = vtkMRMLScene()
        self.scene.AddObserver(
            vtkMRMLScene.NodeAboutToBeRemovedEvent,
            self._remove_attached_displayable_nodes,
        )

        # Add one crosshair to the scene
        # Copied from qSlicerCoreApplication::setMRMLScene
        crosshair = vtkMRMLCrosshairNode()
        crosshair.SetCrosshairName("default")
        self.scene.AddNode(crosshair)

        # Create application logic
        self.app_logic = vtkSlicerApplicationLogic()
        self.app_logic.SetMRMLScene(self.scene)
        self.app_logic.GetColorLogic().SetMRMLScene(self.scene)
        self.app_logic.GetColorLogic().AddDefaultColorNodes()

        self.app_logic.SetSliceLogics(vtkCollection())
        self.app_logic.SetViewLogics(vtkCollection())

        # Connect 3D and 2D view displayable manager factories
        vtkMRMLThreeDViewDisplayableManagerFactory.GetInstance().SetMRMLApplicationLogic(
            self.app_logic
        )
        vtkMRMLSliceViewDisplayableManagerFactory.GetInstance().SetMRMLApplicationLogic(
            self.app_logic
        )

        # Create colors logic
        self.color_logic = vtkMRMLColorLogic()
        self.color_logic.SetMRMLApplicationLogic(self.app_logic)
        self.color_logic.SetMRMLScene(self.scene)
        self.app_logic.SetModuleLogic("Colors", self.color_logic)

        # Create volume rendering
        self.volume_rendering = VolumeRendering(
            self.scene, self.app_logic, self.share_directory.as_posix()
        )

        # Create markups logic
        self.markups_logic = vtkSlicerMarkupsLogic()
        self.markups_logic.SetMRMLApplicationLogic(self.app_logic)
        self.markups_logic.SetMRMLScene(self.scene)
        self.app_logic.SetModuleLogic("Markups", self.markups_logic)

        # Initialize volumes logic
        self.volumes_logic = vtkSlicerVolumesLogic()
        self.volumes_logic.SetMRMLScene(self.scene)
        self.volumes_logic.SetMRMLApplicationLogic(self.app_logic)
        self.app_logic.SetModuleLogic("Volumes", self.volumes_logic)

        # Set up Terminologies logic (needed for subject hierarchy tree view color/terminology selector)
        self.terminologies_logic = vtkSlicerTerminologiesModuleLogic()
        self.terminologies_logic.SetModuleShareDirectory(
            self.share_directory.joinpath("terminologies").as_posix()
        )
        self.terminologies_logic.SetMRMLScene(self.scene)
        self.terminologies_logic.SetMRMLApplicationLogic(self.app_logic)
        self.app_logic.SetModuleLogic("Terminologies", self.terminologies_logic)

        # Initialize subject hierarchy logic
        self.sh_module_logic = vtkSlicerSubjectHierarchyModuleLogic()
        self.sh_module_logic.SetMRMLScene(self.scene)
        self.sh_module_logic.SetMRMLApplicationLogic(self.app_logic)

        # Initialize orientation definitions
        patient_right_is_screen_left = True
        vtkMRMLSliceNode.AddDefaultSliceOrientationPresets(
            self.scene,
            patient_right_is_screen_left,
        )

        # initialize view manager responsible for creating new views in the app
        self.view_manager = ViewManager(self.scene, self.app_logic)

        # Initialize IO manager
        self.io_manager = IOManager(self.scene, self.app_logic)

        # Initialize display manager
        self.display_manager = DisplayManager(self.view_manager, self.volume_rendering)

    @vtk.calldata_type(vtk.VTK_OBJECT)
    def _remove_attached_displayable_nodes(self, scene, eventid, node):
        if not scene:
            return

        if not hasattr(node, "GetNumberOfDisplayNodes"):
            return

        for i_display_node in range(node.GetNumberOfDisplayNodes()):
            scene.RemoveNode(node.GetNthDisplayNode(i_display_node))
