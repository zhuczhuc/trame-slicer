import asyncio
from asyncio import Queue
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import Pool
from pathlib import Path
from time import sleep
from unittest.mock import MagicMock

import pytest
from trame_server.utils.asynchronous import create_task

from slicer_trame.components.rca_render_scheduler import (
    RcaRenderScheduler,
    encode_np_img_to_jpg,
    encode_np_img_to_jpg_with_meta,
    render_to_image,
    time_now_ms,
    vtk_img_to_numpy_array,
)


def test_a_view_can_be_encoded_to_jpg(a_threed_view, tmpdir):
    img = encode_np_img_to_jpg(
        *vtk_img_to_numpy_array(render_to_image(a_threed_view.render_window())), 100
    )
    with open(Path(tmpdir).joinpath("test_img.jpg"), "wb") as f:
        f.write(img)


def test_np_encode_can_be_done_using_multiprocess(a_threed_view):
    array, cols, rows = vtk_img_to_numpy_array(
        render_to_image(a_threed_view.render_window())
    )
    now_ms = time_now_ms()

    with Pool(1) as p:
        encoded, meta, ret_now_ms = p.apply(
            encode_np_img_to_jpg_with_meta,
            args=(array, cols, rows, 100, now_ms),
        )
        assert meta
        assert meta["st"] == now_ms
        assert ret_now_ms == now_ms
        assert encoded


def pool_sleep(t_sleep_s):
    sleep(t_sleep_s)
    return 1, 2, 3


@pytest.mark.asyncio
async def test_multi_processing_apply_async_is_compatible_with_async_queue():
    q = Queue()
    running = Queue()
    await running.put(True)
    mock = MagicMock()
    pool_result_mock = MagicMock()

    with ProcessPoolExecutor(1) as p:

        async def wait_pool():
            result = await q.get()
            result = await result
            pool_result_mock(*result)

        async def push_to_pool():
            await q.put(asyncio.wrap_future(p.submit(pool_sleep, 3)))

        async def proc():
            while not running.empty():
                mock()
                await asyncio.sleep(0.1)

        create_task(push_to_pool())
        create_task(wait_pool())
        proc_task = create_task(proc())

        await asyncio.sleep(4)
        await running.get()
        await proc_task
        assert mock.call_count > 10
        pool_result_mock.assert_called_with(1, 2, 3)


@pytest.mark.asyncio
async def test_after_request_render_pushes_render_followed_by_still_render(
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
    )

    try:
        await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 2
        assert a_mock_push.call_args_list[0].args[1]["quality"] == 0
        assert a_mock_push.call_args_list[1].args[1]["quality"] == 100
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_when_schedule_render_called_before_still_render_keeps_animating(
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
    )

    try:
        await scheduler.async_schedule_render()
        await asyncio.sleep(0.1)
        await scheduler.async_schedule_render()
        await asyncio.sleep(0.1)
        await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 4
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_if_no_render_is_scheduled_doesnt_push(
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
    )

    try:
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 0
    finally:
        await scheduler.close()


@pytest.mark.asyncio
async def test_groups_close_request_render_together(
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
    )

    try:
        for _ in range(30):
            await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 2
    finally:
        await scheduler.close()
