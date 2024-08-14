import pytest
from vtkmodules.vtkMRMLCore import vtkMRMLScene
from vtkmodules.vtkSlicerBaseLogic import vtkSlicerApplicationLogic

from slicer_trame.components.layout_grid import (
    SlicerView,
    SlicerViewType,
    SlicerViewProps,
)
from slicer_trame.slicer import ViewManager


@pytest.fixture()
def a_view_manager():
    return ViewManager(vtkMRMLScene(), vtkSlicerApplicationLogic())


@pytest.fixture()
def a_2d_view():
    return SlicerView("2d_view", SlicerViewType.SLICE_VIEW, SlicerViewProps())


@pytest.fixture()
def a_3d_view():
    return SlicerView("2d_view", SlicerViewType.THREE_D_VIEW, SlicerViewProps())


def test_view_manager_uses_first_capable_factory_when_creating_view():
    raise NotImplementedError()


def test_view_manager_returns_existing_view_if_created():
    raise NotImplementedError()


def test_view_manager_creates_view_if_requested_not_created():
    raise NotImplementedError()


def test_view_manager_created_nodes_are_added_to_slicer_scene():
    raise NotImplementedError()


def test_view_manager_created_views_are_added_to_template():
    raise NotImplementedError()
