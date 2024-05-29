import vtk
from vtkmodules.vtkMRMLCore import vtkMRMLSliceNode, vtkMRMLScene, vtkMRMLVolumeArchetypeStorageNode
from vtkmodules.vtkMRMLLogic import vtkMRMLSliceLogic
from vtkmodules.vtkRenderingCore import vtkImageMapper, vtkActor2D
from vtkmodules.vtkSlicerBaseLogic import vtkSlicerApplicationLogic

scene = vtkMRMLScene()
app_logic = vtkSlicerApplicationLogic()
app_logic.SetMRMLScene(scene)
app_logic.GetColorLogic().SetMRMLScene(scene)
app_logic.GetColorLogic().AddDefaultColorNodes()

storage_node = vtkMRMLVolumeArchetypeStorageNode()
scalarNode = scene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
storage_node.SetFileName(r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\MRHead.nrrd")
storage_node.ReadData(scalarNode)
scalarNode.SetAndObserveStorageNodeID(storage_node.GetID())
scalarNode.CreateDefaultDisplayNodes()

sliceLogic = vtkMRMLSliceLogic()
sliceLogic.SetMRMLScene(scene)
sliceLogic.AddSliceNode("Red")

sliceNode = sliceLogic.GetSliceNode()
sliceNode.SetSliceResolutionMode(vtkMRMLSliceNode.SliceResolutionMatch2DView)
sliceNode.SetOrientation("Coronal")

sliceCompositeNode = sliceLogic.GetSliceCompositeNode()
sliceCompositeNode.SetBackgroundVolumeID(scalarNode.GetID())

sliceLogic.FitSliceToAll()


def display_working():
    viewer = vtk.vtkImageViewer2()
    viewer.SetInputConnection(sliceLogic.GetImageDataConnection())
    viewer.GetRenderer().SetBackground(1.0, 1.0, 1.0)
    rw = viewer.GetRenderWindow()

    ri = vtk.vtkRenderWindowInteractor()
    viewer.SetupInteractor(ri)

    rw.Render()
    ri.Start()


def display_test():
    image_mapper = vtkImageMapper()
    image_mapper.SetInputConnection(sliceLogic.GetImageDataConnection())
    image_actor = vtkActor2D()
    image_actor.SetMapper(image_mapper)
    image_actor.GetProperty().SetDisplayLocationToBackground()

    rw = vtk.vtkRenderWindow()
    rr = vtk.vtkRenderer()
    rr.SetBackground(1.0, 1.0, 1.0)

    rw.AddRenderer(rr)
    ri = vtk.vtkRenderWindowInteractor()
    ri.SetRenderWindow(rw)

    rw.Render()
    ri.Start()


display_working()
