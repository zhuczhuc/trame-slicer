from copy import deepcopy

import numpy as np
import pytest

from slicer_trame.core.volume_property import VRShiftMode


@pytest.fixture
def a_volume_rendering(a_slicer_app):
    return a_slicer_app.volume_rendering


def test_volume_rendering_can_create_display_node(a_volume_node, a_volume_rendering):
    display_node = a_volume_rendering.create_display_node(a_volume_node)
    assert display_node


def test_volume_rendering_can_apply_preset(a_volume_node, a_volume_rendering):
    display_node = a_volume_rendering.create_display_node(a_volume_node)
    prop = a_volume_rendering.get_volume_node_property(a_volume_node)
    colors = prop.get_color_map_values()

    a_volume_rendering.apply_preset(display_node, "MR-Default")
    mr_default_colors = prop.get_color_map_values()
    assert not np.allclose(colors, mr_default_colors)
    assert not np.allclose(mr_default_colors[0], mr_default_colors[1])

    a_volume_rendering.apply_preset(display_node, "MR-Angio")
    assert not np.allclose(mr_default_colors, prop.get_color_map_values())


def test_volume_rendering_can_shift_vr_from_preset(a_volume_node, a_volume_rendering):
    a_volume_rendering.create_display_node(a_volume_node, "MR-Default")
    prop = a_volume_rendering.get_volume_node_property(a_volume_node)
    exp_colors = [
        [color[0] + 42.0, *color[1:]] for color in prop.get_color_map_values()
    ]
    exp_opacities = [
        [opacity[0] + 42.0, *opacity[1:]] for opacity in prop.get_opacity_map_values()
    ]

    a_volume_rendering.set_absolute_vr_shift_from_preset(
        a_volume_node, "MR-Default", 42.0
    )
    assert np.allclose(exp_colors, prop.get_color_map_values())
    assert np.allclose(exp_opacities, prop.get_opacity_map_values())


def test_volume_rendering_can_shift_vr_relative_to_current(
    a_volume_node, a_volume_rendering
):
    a_volume_rendering.create_display_node(a_volume_node, "MR-Default")
    prop = a_volume_rendering.get_volume_node_property(a_volume_node)
    exp_colors = [
        [color[0] + 100.0, *color[1:]] for color in prop.get_color_map_values()
    ]
    exp_opacities = [
        [opacity[0] + 100.0, *opacity[1:]] for opacity in prop.get_opacity_map_values()
    ]

    a_volume_rendering.set_relative_vr_shift(a_volume_node, 42.0)
    a_volume_rendering.set_relative_vr_shift(a_volume_node, 58.0)
    assert np.allclose(exp_colors, prop.get_color_map_values())
    assert np.allclose(exp_opacities, prop.get_opacity_map_values())


def test_volume_rendering_can_shift_vr_independently(a_volume_node, a_volume_rendering):
    a_volume_rendering.create_display_node(a_volume_node, "MR-Default")
    prop = a_volume_rendering.get_volume_node_property(a_volume_node)
    opacities = deepcopy(prop.get_opacity_map_values())
    exp_colors = [
        [color[0] + 42.0, *color[1:]] for color in prop.get_color_map_values()
    ]

    a_volume_rendering.set_relative_vr_shift(a_volume_node, 42.0, VRShiftMode.COLOR)
    assert np.allclose(exp_colors, prop.get_color_map_values())
    assert np.allclose(opacities, prop.get_opacity_map_values())

    exp_opacities = [[opacity[0] - 42.0, *opacity[1:]] for opacity in opacities]
    a_volume_rendering.set_relative_vr_shift(a_volume_node, -42.0, VRShiftMode.OPACITY)
    assert np.allclose(exp_colors, prop.get_color_map_values())
    assert np.allclose(exp_opacities, prop.get_opacity_map_values())


def test_volume_rendering_returns_vr_range(a_volume_node, a_volume_rendering):
    min_vr, max_vr = a_volume_rendering.get_vr_shift_range(a_volume_node)
    assert min_vr != -1
    assert max_vr != 1
