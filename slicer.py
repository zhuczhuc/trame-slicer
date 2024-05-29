from vtkmodules.vtkIOGeometry import vtkSTLReader
from vtkmodules.vtkIOXML import vtkXMLPolyDataReader
from vtkmodules.vtkMRMLCore import *
from vtkmodules.vtkMRMLDisplayableManager import *
from vtkmodules.vtkMRMLLogic import *
from vtkmodules.vtkRenderingCore import vtkRenderer, vtkRenderWindow, vtkRenderWindowInteractor

reader = vtkSTLReader()
reader.SetFileName(r"C:\Work\Projects\Acandis\POC_SlicerLib_Trame\model.stl")
reader.Update()
polydata = reader.GetOutput()

rr = vtkRenderer()
rw = vtkRenderWindow()
ri = vtkRenderWindowInteractor()

iStyle = vtkMRMLViewInteractorStyle()
iStyle = vtkMRMLThreeDViewInteractorStyle()
print(vtkTagTableCollection().__class__.__mro__)
rw.AddRenderer(rr)
rw.SetInteractor(ri)
# ri.SetInteractorStyle(iStyle)

scene = vtkMRMLScene()
applicationLogic = vtkMRMLApplicationLogic()
applicationLogic.SetMRMLScene(scene)

viewNode = vtkMRMLViewNode()
scene.AddNode(viewNode)

displayableManagerGroup = vtkMRMLDisplayableManagerGroup()
displayableManagerGroup.SetRenderer(rr)
displayableManagerGroup.SetMRMLDisplayableNode(viewNode)

vrDisplayableManager = vtkMRMLModelDisplayableManager()
vrDisplayableManager.SetMRMLApplicationLogic(applicationLogic)
displayableManagerGroup.AddDisplayableManager(vrDisplayableManager)

vrDisplayableCamera = vtkMRMLCameraDisplayableManager()
vrDisplayableCamera.SetMRMLApplicationLogic(applicationLogic)
displayableManagerGroup.AddDisplayableManager(vrDisplayableCamera)

displayableManagerGroup.GetInteractor().Initialize()
iStyle.SetDisplayableManagers(displayableManagerGroup)

modelNode = scene.AddNewNodeByClass("vtkMRMLModelNode")
modelNode.SetAndObservePolyData(polydata)
modelNode.CreateDefaultDisplayNodes()

vrDisplayableManager.GetInteractor().Start()
