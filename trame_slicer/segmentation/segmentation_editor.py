import enum
import math
from typing import Optional

import numpy as np
import vtkmodules.util.numpy_support as vtknp
from numpy.typing import NDArray
from slicer import (
    vtkMRMLScalarVolumeNode,
    vtkMRMLSegmentationDisplayNode,
    vtkMRMLSegmentationNode,
    vtkMRMLTransformNode,
    vtkSegmentation,
    vtkSegmentationConverter,
)
from vtkmodules.vtkCommonCore import VTK_UNSIGNED_CHAR, vtkPoints
from vtkmodules.vtkCommonDataModel import vtkImageData, vtkPolyData
from vtkmodules.vtkCommonMath import vtkMatrix4x4
from vtkmodules.vtkCommonTransforms import vtkTransform
from vtkmodules.vtkFiltersGeneral import vtkTransformPolyDataFilter
from vtkmodules.vtkFiltersModeling import vtkFillHolesFilter
from vtkmodules.vtkImagingCore import vtkImageConstantPad
from vtkmodules.vtkImagingStencil import (
    vtkImageStencilToImage,
    vtkPolyDataToImageStencil,
)


def vtk_image_to_np(image: vtkImageData) -> np.ndarray:
    dims = tuple(reversed(image.GetDimensions()))
    return vtknp.vtk_to_numpy(image.GetPointData().GetScalars()).reshape(dims)


def _clamp_extent(extent: list[int], limits: list[int]) -> list[int]:
    return [
        max(extent[0], limits[0]),
        min(extent[1], limits[1]),
        max(extent[2], limits[2]),
        min(extent[3], limits[3]),
        max(extent[4], limits[4]),
        min(extent[5], limits[5]),
    ]


# Convert a vtkImageData subextent to NumPy slices
def _subextent_to_slices(
    extent: list[int], subextent: list[int]
) -> tuple[slice, slice, slice]:
    return (
        slice(
            subextent[4] - extent[4],
            subextent[4] - extent[4] + (subextent[5] - subextent[4] + 1),
        ),
        slice(
            subextent[2] - extent[2],
            subextent[2] - extent[2] + (subextent[3] - subextent[2] + 1),
        ),
        slice(
            subextent[0] - extent[0],
            subextent[0] - extent[0] + (subextent[1] - subextent[0] + 1),
        ),
    )


class LabelMapOperation(enum.IntEnum):
    Erase = 0
    Set = 1


class LabelMapOverwriteMode(enum.IntEnum):
    # Areas added to selected segment will be removed from all other segments. (no overlap)
    AllSegments = 0
    # Areas added to selected segment will be removed from all visible segments. (no overlap with visible, overlap possible with hidden)
    VisibleSegments = 1
    # Areas added to selected segment will not be removed from any segments. (overlap with all other segments)
    Never = 2


class SegmentationEditor:
    """
    Edits a segmentation node
    """

    def __init__(
        self,
        segmentation_node: vtkMRMLSegmentationNode,
        source_volume_node: vtkMRMLScalarVolumeNode,
    ) -> None:
        self._segmentation_node = segmentation_node
        self._segmentation: vtkSegmentation = self._segmentation_node.GetSegmentation()
        self._source_volume_node = source_volume_node
        self._active_segment = (
            self._segmentation.GetNthSegmentID(0)
            if self._segmentation.GetNumberOfSegments() > 0
            else ""
        )
        self._mask = None
        self._operation = LabelMapOperation.Set
        self._overwrite_mode = LabelMapOverwriteMode.AllSegments

    @property
    def segmentation_node(self) -> vtkMRMLSegmentationNode:
        return self._segmentation_node

    @property
    def segmentation(self) -> vtkSegmentation:
        return self._segmentation

    @property
    def volume_node(self) -> vtkMRMLScalarVolumeNode:
        return self._source_volume_node

    @volume_node.setter
    def volume_node(self, node: vtkMRMLScalarVolumeNode) -> None:
        self._source_volume_node = node

    @property
    def active_segment(self) -> str:
        return self._active_segment

    @active_segment.setter
    def active_segment(self, id) -> None:
        self._active_segment = id

    @property
    def mask(self) -> Optional[NDArray[np.bool]]:
        return self._mask

    @mask.setter
    def mask(self, val: Optional[NDArray[np.bool]]):
        if val is not None and tuple(val.shape) != tuple(
            reversed(self._source_volume_node.GetImageData().GetDimensions())
        ):
            raise ValueError("mask extent must match source volume extent")

        self._mask = val

    @property
    def operation(self) -> LabelMapOperation:
        return self._operation

    @operation.setter
    def operation(self, op: LabelMapOperation) -> None:
        self._operation = op

    @property
    def overwrite_mode(self) -> LabelMapOverwriteMode:
        return self._overwrite_mode

    @overwrite_mode.setter
    def overwrite_mode(self, mode: LabelMapOverwriteMode) -> None:
        self._overwrite_mode = mode

    def sanize_segmentation(self):
        """
        Force labelmap extent to source volume extent.\n
        Does nothing if segmentation contains no segment.
        """
        if self._segmentation.GetNumberOfSegments() == 0:
            return

        segment = self._segmentation.GetNthSegment(0)
        repr_name = (
            vtkSegmentationConverter.GetSegmentationBinaryLabelmapRepresentationName()
        )
        representation: vtkImageData = segment.GetRepresentation(repr_name)
        if representation is None:
            self._segmentation.CreateRepresentation(repr_name, True)
            representation: vtkImageData = segment.GetRepresentation(repr_name)

        padder = vtkImageConstantPad()
        padder.SetInputData(representation)
        padder.SetConstant(0.0)
        padder.SetOutputWholeExtent(
            list(self._source_volume_node.GetImageData().GetExtent())
        )
        padder.Update()

        # All segments must share the same labelmap.
        # This shallow copy will update the extent and scalars for all segment!
        representation.ShallowCopy(padder.GetOutput())

    def enable_surface_representation(self):
        repr_name = (
            vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
        )
        self._segmentation.CreateRepresentation(repr_name, True)

    def disable_surface_representation(self):
        repr_name = (
            vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
        )
        if self._segmentation.ContainsRepresentation(repr_name):
            self._segmentation.RemoveRepresentation(repr_name)

    def update_surface_representation(self) -> bool:
        repr_name = (
            vtkSegmentationConverter.GetSegmentationClosedSurfaceRepresentationName()
        )
        if self._segmentation.ContainsRepresentation(repr_name):
            self._segmentation.CreateRepresentation(repr_name, True)
            return True

        return False

    # poly: in world origin coordinates (no transform but world-coords sized)
    # world locations: each location where glyph will be rendered at (world-coords)
    def apply_glyph(self, poly: vtkPolyData, world_locations: vtkPoints) -> None:
        if self._active_segment == "":
            print("Warning: no active segment in apply_poly_glyph")
            return

        if world_locations.GetNumberOfPoints() == 0:
            print("Warning: no points")
            return

        # Rotate poly to later be translated in ijk coordinates for each world_locations
        world_to_ijk_transform_matrix = vtkMatrix4x4()
        self._source_volume_node.GetIJKToRASMatrix(world_to_ijk_transform_matrix)
        world_to_ijk_transform_matrix.Invert()
        world_to_ijk_transform_matrix.SetElement(0, 3, 0)
        world_to_ijk_transform_matrix.SetElement(1, 3, 0)
        world_to_ijk_transform_matrix.SetElement(2, 3, 0)

        world_to_segmentation_transform_matrix = vtkMatrix4x4()
        world_to_segmentation_transform_matrix.Identity()
        vtkMRMLTransformNode.GetMatrixTransformBetweenNodes(
            None,  # noqa This parameter can be null
            self._segmentation_node.GetParentTransformNode(),
            world_to_segmentation_transform_matrix,
        )
        world_to_segmentation_transform_matrix.SetElement(0, 3, 0)
        world_to_segmentation_transform_matrix.SetElement(1, 3, 0)
        world_to_segmentation_transform_matrix.SetElement(2, 3, 0)

        world_origin_to_modifier_labelmap_ijk_transform = vtkTransform()
        world_origin_to_modifier_labelmap_ijk_transform.Concatenate(
            world_to_ijk_transform_matrix
        )
        world_origin_to_modifier_labelmap_ijk_transform.Concatenate(
            world_to_segmentation_transform_matrix
        )

        world_origin_to_modifier_labelmap_ijk_transformer = vtkTransformPolyDataFilter()
        world_origin_to_modifier_labelmap_ijk_transformer.SetTransform(
            world_origin_to_modifier_labelmap_ijk_transform
        )
        world_origin_to_modifier_labelmap_ijk_transformer.SetInputData(poly)
        world_origin_to_modifier_labelmap_ijk_transformer.Update()

        # Pre-rotated polydata
        brush_model: vtkPolyData = (
            world_origin_to_modifier_labelmap_ijk_transformer.GetOutput()
        )

        modifier_labelmap = self._poly_to_modifier_labelmap(brush_model)
        original_extent = modifier_labelmap.GetExtent()
        np_modifier_labelmap = vtk_image_to_np(modifier_labelmap) != 0

        points_ijk = self._world_points_to_ijk(world_locations)
        for i in range(points_ijk.GetNumberOfPoints()):
            position = points_ijk.GetPoint(i)
            # translate the modifier labelmap in IJK coords
            extent = [
                original_extent[0] + int(position[0]),
                original_extent[1] + int(position[0]),
                original_extent[2] + int(position[1]),
                original_extent[3] + int(position[1]),
                original_extent[4] + int(position[2]),
                original_extent[5] + int(position[2]),
            ]
            self.apply_binary_labelmap(np_modifier_labelmap, extent)

    # poly in world coordinates
    def apply_poly(self, poly_world: vtkPolyData):
        if self._active_segment == "":
            return

        poly_ijk = self._world_poly_to_ijk(poly_world)
        modifier_labelmap = self._poly_to_modifier_labelmap(poly_ijk)

        self.apply_labelmap(modifier_labelmap)

    def apply_labelmap(self, modifier_labelmap: vtkImageData):
        # modifier_labelmap: in source ijk coordinates, VTK image data version

        np_modifier_labelmap = vtk_image_to_np(modifier_labelmap) != 0
        self.apply_binary_labelmap(
            np_modifier_labelmap, list(modifier_labelmap.GetExtent())
        )

    def apply_binary_labelmap(
        self, modifier_labelmap: NDArray[np.bool], base_modifier_extent: list[int]
    ):
        # modifier_labelmap: in source ijk coordinates
        if self._active_segment == "":
            return

        segment = self._segmentation.GetSegment(self._active_segment)
        labelmap: vtkImageData = segment.GetRepresentation(
            vtkSegmentationConverter.GetBinaryLabelmapRepresentationName()
        )

        common_extent = list(labelmap.GetExtent())
        # clamp modifier extent to common extent so we don't draw outside the segmentation!
        modifier_extent = _clamp_extent(base_modifier_extent, common_extent)

        np_labelmap = vtk_image_to_np(labelmap)
        labelmap_slices = _subextent_to_slices(common_extent, modifier_extent)
        modifier_labelmap_slices = _subextent_to_slices(
            base_modifier_extent, modifier_extent
        )

        if any(s.stop - s.start <= 0 for s in labelmap_slices) or any(
            s.stop - s.start <= 0 for s in modifier_labelmap_slices
        ):
            # nothing to do, affected labelmap area is empty or out of labelmap range
            return

        label_value = (
            segment.GetLabelValue() if self._operation == LabelMapOperation.Set else 0
        )

        # Apply effect
        self._apply_modifier_labelmap_to_labelmap(
            np_labelmap[labelmap_slices],
            modifier_labelmap[modifier_labelmap_slices],
            self._mask[labelmap_slices] if self._mask else None,
            label_value,
            self._overwrite_mode,
        )

        labelmap.GetPointData().GetScalars().Modified()

    def _apply_modifier_labelmap_to_labelmap(
        self,
        labelmap: np.ndarray,
        modifier: NDArray[np.bool],
        mask: Optional[NDArray[np.bool]],
        label_value: int,
        rule: LabelMapOverwriteMode,
    ) -> None:
        """even if you can call this function, you should use one of the higher level function defined above"""

        masked_modifier = mask & modifier if mask else modifier
        if rule == LabelMapOverwriteMode.AllSegments:
            labelmap[masked_modifier] = label_value
        elif rule == LabelMapOverwriteMode.VisibleSegments:
            display_node: vtkMRMLSegmentationDisplayNode = (
                self.segmentation_node.GetDisplayNode()
            )
            segments_count = self.segmentation.GetNumberOfSegments()
            for i in range(segments_count):
                if display_node.GetSegmentVisibility(
                    self.segmentation.GetNthSegmentID(i)
                ):
                    segment_label = self.segmentation.GetNthSegment(i).GetLabelValue()
                    segment_label_mask = (
                        labelmap == segment_label
                    )  # create a mask for the segment value
                    labelmap[masked_modifier & segment_label_mask] = label_value
        elif rule == LabelMapOverwriteMode.Never:
            empty_label_mask = labelmap == 0
            labelmap[masked_modifier & empty_label_mask] = label_value

    def _poly_to_modifier_labelmap(self, poly: vtkPolyData) -> vtkImageData:
        filler = vtkFillHolesFilter()
        filler.SetInputData(poly)
        filler.SetHoleSize(4096.0)
        filler.Update()
        filled_poly = filler.GetOutput()

        bounds = filled_poly.GetBounds()
        extent = [
            int(math.floor(bounds[0])) - 1,
            int(math.ceil(bounds[1])) + 1,
            int(math.floor(bounds[2])) - 1,
            int(math.ceil(bounds[3])) + 1,
            int(math.floor(bounds[4])) - 1,
            int(math.ceil(bounds[5])) + 1,
        ]
        brush_poly_data_to_stencil = vtkPolyDataToImageStencil()
        brush_poly_data_to_stencil.SetInputData(filled_poly)
        brush_poly_data_to_stencil.SetOutputSpacing(1.0, 1.0, 1.0)
        brush_poly_data_to_stencil.SetOutputWholeExtent(extent)

        stencilToImage = vtkImageStencilToImage()
        stencilToImage.SetInputConnection(brush_poly_data_to_stencil.GetOutputPort())
        stencilToImage.SetInsideValue(1.0)
        stencilToImage.SetOutsideValue(0.0)
        stencilToImage.SetOutputScalarType(VTK_UNSIGNED_CHAR)
        stencilToImage.Update()

        return stencilToImage.GetOutput()

    def _world_points_to_ijk(self, points: vtkPoints) -> vtkPoints:
        world_to_ijk_transform_matrix = vtkMatrix4x4()
        self._source_volume_node.GetIJKToRASMatrix(world_to_ijk_transform_matrix)
        world_to_ijk_transform_matrix.Invert()

        world_to_ijk_transform = vtkTransform()
        world_to_ijk_transform.Identity()
        world_to_ijk_transform.Concatenate(world_to_ijk_transform_matrix)

        ijk_points = vtkPoints()
        world_to_ijk_transform.TransformPoints(points, ijk_points)

        return ijk_points

    def _world_poly_to_ijk(self, poly: vtkPolyData) -> vtkPolyData:
        world_to_ijk_transform_matrix = vtkMatrix4x4()
        self._source_volume_node.GetIJKToRASMatrix(world_to_ijk_transform_matrix)
        world_to_ijk_transform_matrix.Invert()

        world_to_ijk_transform = vtkTransform()
        world_to_ijk_transform.Identity()
        world_to_ijk_transform.Concatenate(world_to_ijk_transform_matrix)

        poly_transformer = vtkTransformPolyDataFilter()
        poly_transformer.SetInputData(poly)
        poly_transformer.SetTransform(world_to_ijk_transform)
        poly_transformer.Update()

        return poly_transformer.GetOutput()
