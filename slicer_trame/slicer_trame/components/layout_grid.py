from dataclasses import dataclass
from enum import Enum, auto, unique
from itertools import chain
from typing import Union

from trame.widgets import client, html

from slicer_trame.slicer.abstract_view import ViewProps


class LayoutDirection(Enum):
    Vertical = auto()
    Horizontal = auto()


@dataclass
class View:
    singleton_tag: str


@unique
class SlicerViewType(Enum):
    SLICE_VIEW = "vtkMRMLSliceNode"
    THREE_D_VIEW = "vtkMRMLViewNode"


@dataclass
class SlicerView(View):
    type: SlicerViewType
    properties: ViewProps

    def to_xml(self):
        return f'<view class="{self.type.value}" singletontag="{self.singleton_tag}">{self.properties.to_xml()}</view>'

    @classmethod
    def from_xml(cls, xml_str: str) -> "SlicerView":
        from lxml import etree

        elt = etree.fromstring(xml_str)

        properties = {child.get("name"): child.text for child in elt.getchildren()}
        return cls(
            singleton_tag=elt.get("singletontag"),
            type=SlicerViewType(elt.get("class")),
            properties=ViewProps.from_xml_dict(properties),
        )


@dataclass
class Layout:
    direction: LayoutDirection
    items: list[Union["Layout", View]]

    def get_views(self, is_recursive: bool) -> list[View]:
        """
        Returns every views contained in Layout as a flat list.
        :param is_recursive: If true, returns sub layout views as well. Otherwise returns only direct views.
        """
        views = [item for item in self.items if isinstance(item, View)]
        if not is_recursive:
            return views

        sub_views = list(
            chain(
                *[
                    item.get_views(is_recursive)
                    for item in self.items
                    if isinstance(item, Layout)
                ]
            )
        )
        return views + sub_views

    @classmethod
    def empty_layout(cls):
        return cls(LayoutDirection.Vertical, [])


class LayoutGrid:
    """
    Component responsible for displaying view grids.
    """

    def __init__(
        self,
        layout_items: list[Union["Layout", View]],
        layout_direction: LayoutDirection,
    ):
        layout_class = (
            "flex-row"
            if layout_direction == LayoutDirection.Horizontal
            else "flex-column"
        )
        with html.Div(
            classes=f"layout-grid-container {layout_class}",
            style="display: flex; flex-direction: column; flex: 1;",
        ):
            for item in layout_items:
                with html.Div(classes="d-flex", style="flex: 1; display: flex;"):
                    if isinstance(item, Layout):
                        LayoutGrid(item.items, item.direction)
                    else:
                        with html.Div(
                            classes="layout-grid-item",
                            style="display: flex; flex: 1; border: 1px solid #222;",
                        ):
                            client.ServerTemplate(name=item.singleton_tag)

    @classmethod
    def create_root_grid_ui(cls, layout: Layout):
        with html.Div(
            classes="d-flex flex-column flex-grow-1 fill-height",
            style="background-color:black;",
        ):
            cls(layout.items, layout.direction)


def pretty_xml(xml_str: str) -> str:
    from lxml import etree

    parser = etree.XMLParser(remove_blank_text=True)
    root = etree.XML(xml_str, parser=parser)
    return etree.tostring(root, pretty_print=True).decode()


def vue_layout_to_slicer(layout: Layout):
    layout_str = f'<layout type="{layout.direction.name.lower()}">'

    item: Union[Layout, SlicerView]
    for item in layout.items:
        item_xml = (
            vue_layout_to_slicer(item) if isinstance(item, Layout) else item.to_xml()
        )
        layout_str += f"<item>{item_xml}</item>"

    layout_str += "</layout>"
    return layout_str


def slicer_layout_to_vue(xml_str: str) -> Layout:
    from lxml import etree

    elt = etree.fromstring(xml_str)

    def to_layout_item(child):
        if not child.tag == "item" or len(child.getchildren()) != 1:
            raise RuntimeError("Invalid input XML layout")

        child = child.getchildren()[0]
        child_xml_str = etree.tostring(child)
        if child.tag == "layout":
            return slicer_layout_to_vue(child_xml_str)
        elif child.tag == "view":
            return SlicerView.from_xml(child_xml_str)

        raise RuntimeError("Invalid input XML layout")

    items = [to_layout_item(child) for child in elt.getchildren()]

    return Layout(direction=LayoutDirection[elt.attrib["type"].title()], items=items)
