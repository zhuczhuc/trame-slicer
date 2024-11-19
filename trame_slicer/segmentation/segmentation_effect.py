from trame_slicer.segmentation.segmentation_editor import SegmentationEditor


class SegmentationEffect:
    def __init__(self, editor: SegmentationEditor) -> None:
        self._editor = editor

    @property
    def editor(self) -> SegmentationEditor:
        return self._editor
