from dataclasses import dataclass
from enum import Enum, unique

from slicer_trame.slicer.abstract_view import ViewOrientation, ViewProps


@unique
class ViewType(Enum):
    SLICE_VIEW = "vtkMRMLSliceNode"
    THREE_D_VIEW = "vtkMRMLViewNode"


@dataclass
class ViewLayoutDefinition:
    singleton_tag: str
    type: ViewType
    properties: ViewProps

    def to_xml(self):
        return f'<view class="{self.type.value}" singletontag="{self.singleton_tag}">{self.properties.to_xml()}</view>'

    @classmethod
    def from_xml(cls, xml_str: str) -> "ViewLayoutDefinition":
        from lxml import etree

        elt = etree.fromstring(xml_str)

        properties = {child.get("name"): child.text for child in elt.getchildren()}
        return cls(
            singleton_tag=elt.get("singletontag"),
            type=ViewType(elt.get("class")),
            properties=ViewProps.from_xml_dict(properties),
        )

    @classmethod
    def slice_view(cls, orientation: ViewOrientation) -> "ViewLayoutDefinition":
        return cls(
            orientation,
            ViewType.SLICE_VIEW,
            ViewProps(orientation=orientation, label=orientation),
        )

    @classmethod
    def axial_view(cls) -> "ViewLayoutDefinition":
        return cls.slice_view("Axial")

    @classmethod
    def coronal_view(cls) -> "ViewLayoutDefinition":
        return cls.slice_view("Coronal")

    @classmethod
    def sagittal_view(cls) -> "ViewLayoutDefinition":
        return cls.slice_view("Sagittal")

    @classmethod
    def threed_view(cls):
        return cls("ThreeD", ViewType.THREE_D_VIEW, ViewProps(label="1"))
