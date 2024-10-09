import asyncio
import time
from asyncio import Queue
from concurrent.futures.process import ProcessPoolExecutor
from multiprocessing import Pool
from typing import Callable

from numpy.typing import NDArray
from trame.app import asynchronous
from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
from vtkmodules.vtkCommonDataModel import vtkImageData
from vtkmodules.vtkIOImage import vtkJPEGWriter
from vtkmodules.vtkRenderingCore import vtkRenderWindow, vtkWindowToImageFilter

from ..slicer.render_scheduler import ScheduledRenderStrategy
from .web_application import RenderingPool


def encode_np_img_to_jpg(image: NDArray, cols: int, rows: int, quality: int) -> bytes:
    """
    Numpy implementation of JPEG conversion of the input image.
    Input image should be a numpy array as extracted from the render to image function.
    This method uses numpy arrays as input for compatibility with Python's multiprocessing.
    """
    if not (cols and rows):
        return b""

    # Convert np image back to vtk image
    vtk_image = vtkImageData()
    vtk_image.SetDimensions(rows, cols, 1)
    vtk_array = numpy_to_vtk(num_array=image, deep=0)
    vtk_image.GetPointData().SetScalars(vtk_array)

    # Use vtkJPEGWriter to encode the image
    writer = vtkJPEGWriter()
    writer.WriteToMemoryOn()
    writer.SetInputData(vtk_image)
    writer.SetQuality(quality)
    writer.Write()

    return bytes(writer.GetResult())


def time_now_ms() -> int:
    return int(time.time_ns() / 1000000)


def encode_np_img_to_jpg_with_meta(
    np_image: NDArray,
    cols: int,
    rows: int,
    quality: int,
    now_ms: int,
) -> tuple[bytes, dict, int]:
    """
    Encodes the input numpy image to JPEG.
    Input image should be a numpy array as extracted from the render to image function.
    This method is compatible with Python's multiprocessing.

    Returns encoded image with the meta information and timestamp for usage in trame.
    """
    meta = dict(
        type="image/jpeg",  # mime type
        codec="",  # video codec, not relevant here
        w=cols,
        h=rows,
        st=now_ms,
        key="key",  # jpegs are always keyframes
        quality=quality,
    )
    return encode_np_img_to_jpg(np_image, cols, rows, quality), meta, now_ms


def render_to_image(view) -> vtkImageData:
    """
    Renders the input vtkRenderWindow to a vtkImageData
    """
    view.Render()
    window_to_image = vtkWindowToImageFilter()
    window_to_image.SetInput(view)
    window_to_image.SetScale(1)
    window_to_image.ReadFrontBufferOff()
    window_to_image.ShouldRerenderOff()
    window_to_image.FixBoundaryOn()
    window_to_image.Update()
    return window_to_image.GetOutput()


def vtk_img_to_numpy_array(image_data: vtkImageData) -> tuple[NDArray, int, int]:
    """
    Converts the input vtkImageData to numpy format.
    """
    rows, cols, _ = image_data.GetDimensions()
    scalars = image_data.GetPointData().GetScalars()
    return vtk_to_numpy(scalars), cols, rows


class RcaRenderScheduler(ScheduledRenderStrategy):
    """
    Render scheduler which renders to image and pushes the rendered encoded image to given input callback.
    JPEG image metadata are pushed along the encoded image.

    Renders synchronously to a vtkImageData, encodes to JPEG in a subprocesses and pushes asynchronously.
    Limits the rendering speed given the target FPS.
    Encodes using interactive quality first and then using 100 quality after a few ticks pass.

    Call the close method to properly stop the scheduler before deleting the object.
    """

    def __init__(
        self,
        push_callback: Callable[[bytes, dict], None],
        window: vtkRenderWindow,
        target_fps: float,
        interactive_quality: int,
        encode_pool: ProcessPoolExecutor = None,
    ):
        super().__init__()

        if not isinstance(window, vtkRenderWindow):
            raise RuntimeError(
                "Invalid input window. "
                "RcaRenderScheduler is only compatible with VTK RenderWindows."
            )

        self._push_callback = push_callback
        self._window = window
        self._target_fps = target_fps
        self._interactive_quality = interactive_quality
        self._still_quality = 100
        self._n_period_until_still_render = 5

        self._last_push_time_ms = time_now_ms()
        self._request_render_queue = Queue()
        self._render_quality_queue = Queue()
        self._push_queue = Queue()

        self._is_closing = False
        self._encode_pool: Pool = encode_pool or RenderingPool.get_singleton()
        self._render_quality_task = asynchronous.create_task(self._render_quality())
        self._render_task = asynchronous.create_task(self._render())
        self._push_task = asynchronous.create_task(self._push())

    @property
    def _target_period_s(self):
        return 1.0 / self._target_fps

    async def close(self):
        # Set closing flag to true and push one final render to make sure every task will have a chance to be canceled.
        if self._is_closing:
            return

        self._is_closing = True
        await self.async_schedule_render()
        await asyncio.sleep(1)
        for task in [self._render_task, self._render_quality_task, self._push_task]:
            await task

    def schedule_render(self):
        asynchronous.create_task(self.async_schedule_render())

    async def async_schedule_render(self):
        await self._request_render_queue.put(True)

    async def _render_quality(self):
        while not self._is_closing:
            await self._request_render_queue.get()
            await self._render_quality_queue.put(self._interactive_quality)
            await self._schedule_still_render()

    async def _schedule_still_render(self):
        await self._empty_request_render_queue()
        for _ in range(self._n_period_until_still_render):
            await asyncio.sleep(self._target_period_s)
            if not self._request_render_queue.empty():
                return
        await self._render_quality_queue.put(self._still_quality)

    async def _empty_request_render_queue(self):
        while not self._request_render_queue.empty():
            await self._request_render_queue.get()

    async def _render(self):
        while not self._is_closing:
            quality = await self._render_quality_queue.get()
            now_ms = time_now_ms()
            np_img, cols, rows = vtk_img_to_numpy_array(render_to_image(self._window))
            await self._push_queue.put(
                asyncio.wrap_future(
                    self._encode_pool.submit(
                        encode_np_img_to_jpg_with_meta,
                        np_img,
                        cols,
                        rows,
                        quality,
                        now_ms,
                    )
                )
            )

    async def _push(self):
        while not self._is_closing:
            result = await self._push_queue.get()
            img, meta, m_time = await result
            if m_time >= self._last_push_time_ms:
                self._last_push_time_ms = m_time
                self._push_callback(img, meta)
