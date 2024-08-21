from unittest import mock

import pytest
from trame.widgets import client
from trame_vuetify.ui.vuetify3 import VAppLayout
from vtkmodules.vtkCommonCore import vtkCollection

from slicer_trame.components.layout_grid import SlicerView, SlicerViewType
from slicer_trame.slicer import SlicerApp, ViewManager
from slicer_trame.slicer.abstract_view import ViewProps
from slicer_trame.slicer.view_factory import (
    IViewFactory,
    RemoteSliceViewFactory,
    RemoteThreeDViewFactory,
)


@pytest.fixture()
def a_slicer_app():
    return SlicerApp()


@pytest.fixture()
def a_view_manager(a_slicer_app):
    return ViewManager(a_slicer_app.scene, a_slicer_app.app_logic)


@pytest.fixture()
def a_2d_view():
    return SlicerView("2d_view", SlicerViewType.SLICE_VIEW, ViewProps())


@pytest.fixture()
def a_3d_view():
    return SlicerView("3d_view", SlicerViewType.THREE_D_VIEW, ViewProps())


def test_view_manager_uses_first_capable_factory_when_creating_view(
    a_view_manager,
    a_2d_view,
):
    f1 = mock.create_autospec(IViewFactory)
    f1.can_create_view.return_value = False

    f2 = mock.create_autospec(IViewFactory)
    f2.can_create_view.return_value = True

    f3 = mock.create_autospec(IViewFactory)
    f3.can_create_view.return_value = True

    a_view_manager.register_factory(f1)
    a_view_manager.register_factory(f2)
    a_view_manager.register_factory(f3)
    a_view_manager.create_view(a_2d_view)

    f2.create_view.assert_called_once()
    f3.create_view.assert_not_called()
    f1.create_view.assert_not_called()


@pytest.fixture()
def a_factory_mock():
    return mock.create_autospec(IViewFactory)


class AView:
    pass


def test_view_manager_returns_existing_view_if_created(
    a_view_manager, a_factory_mock, a_2d_view
):
    a_view_manager.register_factory(a_factory_mock)
    a_factory_mock.can_create_view.return_value = True

    inst = AView()
    a_factory_mock.create_view.side_effect = [inst, None]

    assert a_view_manager.create_view(a_2d_view) == inst
    assert a_view_manager.create_view(a_2d_view) == inst
    a_factory_mock.create_view.assert_called_once()


def test_view_manager_with_default_factories_created_nodes_are_added_to_slicer_scene(
    a_view_manager,
    a_slicer_app,
    a_2d_view,
    a_3d_view,
    a_server,
):
    a_view_manager.register_factory(RemoteSliceViewFactory(a_server))
    a_view_manager.register_factory(RemoteThreeDViewFactory(a_server))

    slice_view = a_view_manager.create_view(a_2d_view)
    threed_view = a_view_manager.create_view(a_3d_view)

    slice_nodes: vtkCollection = a_slicer_app.scene.GetNodesByClass("vtkMRMLSliceNode")
    assert slice_nodes.GetNumberOfItems() == 1
    assert slice_nodes.GetItemAsObject(0) == slice_view.slicer_view.mrml_view_node

    threed_nodes: vtkCollection = a_slicer_app.scene.GetNodesByClass("vtkMRMLViewNode")
    assert threed_nodes.GetNumberOfItems() == 1
    assert threed_nodes.GetItemAsObject(0) == threed_view.slicer_view.mrml_view_node
    a_server.start()


def test_view_manager_created_views_are_added_to_template(
    a_view_manager,
    a_3d_view,
    render_interactive,
    a_server,
):
    a_view_manager.register_factory(RemoteThreeDViewFactory(a_server))

    view = a_view_manager.create_view(a_3d_view)
    view.slicer_view.render_window().Render()
    with VAppLayout(a_server):
        client.ServerTemplate(name=a_3d_view.singleton_tag)

    a_server.start()


def test_a_2d_view_factory_creates_views_with_the_right_properties(
    a_view_manager,
    render_interactive,
    a_server,
):

    a_view_manager.register_factory(RemoteSliceViewFactory(a_server))

    slice_view = SlicerView(
        "view_name",
        SlicerViewType.SLICE_VIEW,
        ViewProps(label="L", orientation="Sagittal", color="#5D8CAE", group=2),
    )
    view = a_view_manager.create_view(slice_view)

    assert view.slicer_view.mrml_view_node.GetOrientation() == "Sagittal"
    assert view.slicer_view.mrml_view_node.GetViewGroup() == 2


def test_2d_factory_views_have_sliders_and_reset_camera_connected_to_slicer(
    a_view_manager,
    render_interactive,
    a_server,
    a_2d_view,
    a_volume_node,
):
    a_view_manager.register_factory(RemoteSliceViewFactory(a_server))
    view = a_view_manager.create_view(a_2d_view)
    view.slicer_view.set_background_volume_id(a_volume_node.GetID())
    vuetify_view_str = str(view.vuetify_view)
    assert "VSlider" in vuetify_view_str
    assert "VBtn" in vuetify_view_str

    with VAppLayout(a_server):
        client.ServerTemplate(name=a_2d_view.singleton_tag)

    assert "slider_value_2d_view" in vuetify_view_str
    assert "slider_max_2d_view" in vuetify_view_str
    assert "slider_min_2d_view" in vuetify_view_str
    assert "slider_step_2d_view" in vuetify_view_str

    assert a_server.state["slider_value_2d_view"] == view.slicer_view.get_slice_value()

    min_range, max_range = view.slicer_view.get_slice_range()
    assert a_server.state["slider_min_2d_view"] == min_range
    assert a_server.state["slider_max_2d_view"] == max_range
    assert a_server.state["slider_step_2d_view"] == view.slicer_view.get_slice_step()

    view.slicer_view.set_slice_value(42)
    assert a_server.state["slider_value_2d_view"] == 42.0

    a_server.start()


def test_3d_view_factory_has_reset_camera_button():
    raise NotImplementedError()


def test_rca_factories_handle_slicer_view_interactive_render():
    raise NotImplementedError()


def test_a_2d_view_slider_updates_vue_sliders():
    raise NotImplementedError()
