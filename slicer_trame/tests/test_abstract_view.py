import vtk
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch

from slicer_trame.app.abstract_view import AbstractView


def test_abstract_view_can_render_a_simple_cone():
    view = AbstractView()
    cone, mapper, actor = vtk.vtkConeSource(), vtk.vtkPolyDataMapper(), vtk.vtkActor()

    cone.Update()
    mapper.SetInputConnection(cone.GetOutputPort())
    actor.SetMapper(mapper)

    style = vtkInteractorStyleSwitch()
    style.SetCurrentStyleToTrackballCamera()
    view.set_interactor_style(style)

    view.render_window()
    view.first_renderer().AddActor(actor)
    view.first_renderer().ResetCamera()
    view.render()
