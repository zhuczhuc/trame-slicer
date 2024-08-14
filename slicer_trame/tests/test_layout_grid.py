import asyncio

import pytest
from trame.app import get_server
from trame_client.widgets.html import Div
from trame_server.utils.asynchronous import create_task
from trame_vuetify.ui.vuetify3 import VAppLayout

from slicer_trame.components.layout_grid import (
    LayoutGrid,
    LayoutDirection,
    View,
    Layout,
    SlicerView,
    SlicerViewType,
    SlicerViewProps,
    pretty_xml,
    vue_layout_to_slicer,
    slicer_layout_to_vue,
)
from slicer_trame.components.view_layout import ViewLayout


async def stop_server(server, stop_time_s):
    await asyncio.sleep(stop_time_s)
    await server.stop()


def test_layout_component_can_display_server_configured_templates(render_interactive):
    server = get_server(None, client_type="vue3")

    with ViewLayout(server, "red_view"):
        Div(style="background-color: red;", classes="fill-height")

    with ViewLayout(server, "blue_view"):
        Div(style="background-color: blue;", classes="fill-height")

    with ViewLayout(server, "green_view"):
        Div(style="background-color: green;", classes="fill-height")

    with VAppLayout(server):
        LayoutGrid.create_root_grid_ui(
            Layout(
                LayoutDirection.Horizontal,
                [
                    View("red_view"),
                    Layout(
                        LayoutDirection.Vertical,
                        [
                            View("blue_view"),
                            View("green_view"),
                        ],
                    ),
                ],
            )
        )

    create_task(stop_server(server, stop_time_s=10 if render_interactive else 0.1))
    server.start()


@pytest.fixture()
def a_slicer_layout():
    return """
<layout type="vertical">
    <item>
        <layout type="horizontal">
            <item>
                <view class="vtkMRMLSliceNode" singletontag="Red">
                    <property name="orientation" action="default">Axial</property>
                    <property name="viewlabel" action="default">R</property>
                    <property name="viewcolor" action="default">#F34A33</property>
                    <property name="viewgroup" action="default">1</property>
                </view>
            </item>
            <item>
                <view class="vtkMRMLViewNode" singletontag="1">
                    <property name="viewlabel" action="default">1</property>
                </view>
            </item>
        </layout>
    </item>
    <item>
        <layout type="horizontal">
            <item>
                <view class="vtkMRMLSliceNode" singletontag="Green">
                    <property name="orientation" action="default">Coronal</property>
                    <property name="viewlabel" action="default">G</property>
                    <property name="viewcolor" action="default">#6EB04B</property>
                </view>
            </item>
            <item>
                <view class="vtkMRMLSliceNode" singletontag="Yellow">
                    <property name="orientation" action="default">Sagittal</property>
                    <property name="viewlabel" action="default">Y</property>
                    <property name="viewcolor" action="default">#EDD54C</property>
                </view>
            </item>
        </layout>
    </item>
</layout>
"""


@pytest.fixture()
def a_red_view():
    return SlicerView(
        "Red",
        SlicerViewType.SLICE_VIEW,
        SlicerViewProps(
            orientation="Axial",
            label="R",
            color="#F34A33",
            group="1",
        ),
    )


@pytest.fixture()
def a_green_view():
    return SlicerView(
        "Green",
        SlicerViewType.SLICE_VIEW,
        SlicerViewProps(
            orientation="Coronal",
            label="G",
            color="#6EB04B",
        ),
    )


@pytest.fixture()
def a_yellow_view():
    return SlicerView(
        "Yellow",
        SlicerViewType.SLICE_VIEW,
        SlicerViewProps(
            orientation="Sagittal",
            label="Y",
            color="#EDD54C",
        ),
    )


@pytest.fixture()
def a_3d_view():
    return SlicerView("1", SlicerViewType.THREE_D_VIEW, SlicerViewProps(label="1"))


@pytest.fixture()
def a_vue_layout(a_red_view, a_green_view, a_yellow_view, a_3d_view):
    return Layout(
        LayoutDirection.Vertical,
        [
            Layout(
                LayoutDirection.Horizontal,
                [
                    a_red_view,
                    a_3d_view,
                ],
            ),
            Layout(
                LayoutDirection.Horizontal,
                [
                    a_green_view,
                    a_yellow_view,
                ],
            ),
        ],
    )


def test_layout_can_return_their_views_recursively(
    a_vue_layout, a_red_view, a_green_view, a_yellow_view, a_3d_view
):
    assert a_vue_layout.get_views(is_recursive=True) == [
        a_red_view,
        a_3d_view,
        a_green_view,
        a_yellow_view,
    ]


def test_layout_can_return_only_direct_views(
    a_vue_layout, a_red_view, a_green_view, a_yellow_view, a_3d_view
):
    layout = Layout(
        LayoutDirection.Vertical,
        [
            a_red_view,
            a_green_view,
            Layout(
                LayoutDirection.Horizontal,
                [
                    a_3d_view,
                    a_yellow_view,
                ],
            ),
        ],
    )

    assert layout.get_views(is_recursive=False) == [a_red_view, a_green_view]


def test_layout_grid_configuration_can_be_converted_to_slicer_format(
    a_slicer_layout,
    a_vue_layout,
):
    assert pretty_xml(vue_layout_to_slicer(a_vue_layout)) == pretty_xml(a_slicer_layout)


def test_layout_slicer_format_can_be_converted_to_layout_grid(
    a_slicer_layout,
    a_vue_layout,
):
    assert slicer_layout_to_vue(a_slicer_layout) == a_vue_layout
