from vtkmodules.vtkMRMLCore import vtkMRMLScene


class IOManager:
    """
    Class responsible for loading files in the scene.
    """

    def __init__(self, scene: vtkMRMLScene):
        self.scene = scene

    def load_volume(self, volume_files):
        raise NotImplementedError()

    def load_model(self, model_files):
        raise NotImplementedError()

    def load_segmentation(self, segmentation_files):
        raise NotImplementedError()
