from vtkmodules.vtkCommonCore import vtkCollection
from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLSliceNode, vtkMRMLCrosshairNode
from vtkmodules.vtkSlicerBaseLogic import vtkSlicerApplicationLogic
from vtkmodules.vtkSlicerVolumeRenderingModuleLogic import vtkSlicerVolumeRenderingLogic

from .io_manager import IOManager
from .view_manager import ViewManager


class SlicerApp:
    """
    Container for the core components of a Slicer application.
    Instantiates the scene, application logic and layout manager.
    Configures the default nodes present in the scene.
    """

    def __init__(self):
        self.scene = vtkMRMLScene()

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

        # Create volume rendering logic
        self.volume_rendering_logic = vtkSlicerVolumeRenderingLogic()
        self.volume_rendering_logic.SetMRMLApplicationLogic(self.app_logic)
        self.volume_rendering_logic.SetMRMLScene(self.scene)
        self.volume_rendering_logic.SetModuleShareDirectory(
            r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\slicer_trame\resources"
        )
        self.volume_rendering_logic.ChangeVolumeRenderingMethod(
            "vtkMRMLGPURayCastVolumeRenderingDisplayNode"
        )

        # Initialize orientation definitions
        vtkMRMLSliceNode.AddDefaultSliceOrientationPresets(self.scene)

        # initialize view manager responsible for creating new views in the app
        self.view_manager = ViewManager(self.scene, self.app_logic)

        # Initialize IO manager
        self.io_manager = IOManager(self.scene)
