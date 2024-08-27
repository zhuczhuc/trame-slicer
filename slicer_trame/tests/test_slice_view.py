from unittest.mock import MagicMock

import numpy as np
import pytest

from slicer_trame.components.web_application import WebApplication


def test_slice_view_can_display_volume(
    a_slice_view,
    a_volume_node,
    a_slicer_app,
    render_interactive,
):
    a_slice_view.set_background_volume_id(a_volume_node.GetID())
    a_slice_view.set_background(1.0, 0.0, 0.0)
    a_slice_view.set_orientation("Coronal")
    a_slice_view.fit_slice_to_all()

    np.testing.assert_array_almost_equal(
        a_slice_view.get_slice_range(), [-121.1, 133.9], decimal=1
    )
    assert a_slice_view.get_slice_step() == 1
    assert a_slice_view.get_slice_value() == pytest.approx(6.9, 0.1)

    a_slice_view.render()
    if render_interactive:
        a_slice_view.start_interactor()


def test_a_slice_view_slice_offset_can_be_set(
    a_slice_view,
    a_volume_node,
    a_slicer_app,
    render_interactive,
):
    a_slice_view.set_background_volume_id(a_volume_node.GetID())
    a_slice_view.set_background(1.0, 0.0, 0.0)
    a_slice_view.set_orientation("Coronal")
    a_slice_view.fit_slice_to_all()
    a_slice_view.set_slice_value(42)
    assert a_slice_view.get_slice_value() == 42


def test_slice_view_can_display_empty(a_slice_view, render_interactive):
    a_slice_view.set_orientation("Coronal")
    a_slice_view.reset_camera()
    a_slice_view.render()

    if render_interactive:
        a_slice_view.start_interactor()


def test_slice_view_is_compatible_with_rca_capture(a_slice_view):
    data = WebApplication().get_singleton().StillRender(a_slice_view.render_window())
    assert data is not None


def test_slice_view_can_register_modified_observers(a_slice_view, a_volume_node):
    mock_obs = MagicMock()
    a_slice_view.add_modified_observer(mock_obs)
    a_slice_view.set_background_volume_id(a_volume_node.GetID())

    a_slice_view.set_orientation("Coronal")

    mock_obs.assert_called_with(a_slice_view)
    mock_obs.reset_mock()

    a_slice_view.remove_modified_observer(mock_obs)

    a_slice_view.set_orientation("Sagittal")
    mock_obs.assert_not_called()


def test_slice_view_foreground_background_opacity_can_be_set():
    raise NotImplementedError()
