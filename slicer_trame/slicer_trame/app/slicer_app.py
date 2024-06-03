from vtkmodules.vtkCommonCore import vtkCollection
from vtkmodules.vtkMRMLCore import vtkMRMLScene, vtkMRMLSliceNode
from vtkmodules.vtkSlicerBaseLogic import vtkSlicerApplicationLogic


class SlicerApp:
    def __init__(self):
        self.scene = vtkMRMLScene()

        self.app_logic = vtkSlicerApplicationLogic()
        self.app_logic.SetMRMLScene(self.scene)
        self.app_logic.GetColorLogic().SetMRMLScene(self.scene)
        self.app_logic.GetColorLogic().AddDefaultColorNodes()

        self.app_logic.SetSliceLogics(vtkCollection())
        self.app_logic.SetViewLogics(vtkCollection())

        vtkMRMLSliceNode.AddDefaultSliceOrientationPresets(self.scene)
