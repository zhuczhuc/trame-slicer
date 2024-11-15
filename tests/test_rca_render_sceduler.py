import asyncio
from multiprocessing import Pool
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

from slicer_trame.rca_view import (
    RcaEncoder,
    RcaRenderScheduler,
    encode_np_img_to_bytes,
    encode_np_img_to_format_with_meta,
    render_to_image,
    time_now_ms,
    vtk_img_to_numpy_array,
)


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_a_view_can_be_encoded_to_format(a_threed_view, tmpdir, img_format):
    img = encode_np_img_to_bytes(
        *vtk_img_to_numpy_array(render_to_image(a_threed_view.render_window())),
        img_format,
        100,
    )
    dest_file = Path(tmpdir).joinpath(f"test_img.{img_format}")
    with open(dest_file, "wb") as f:
        f.write(img)

    assert dest_file.is_file()
    im = Image.open(dest_file)
    assert im


@pytest.mark.parametrize("img_format", ["jpeg", "png", "avif", "webp"])
def test_np_encode_can_be_done_using_multiprocess(a_threed_view, img_format):
    array, cols, rows = vtk_img_to_numpy_array(
        render_to_image(a_threed_view.render_window())
    )
    now_ms = time_now_ms()

    with Pool(1) as p:
        encoded, meta, ret_now_ms = p.apply(
            encode_np_img_to_format_with_meta,
            args=(array, img_format, cols, rows, 100, now_ms),
        )
        assert meta
        assert meta["st"] == now_ms
        assert ret_now_ms == now_ms
        assert encoded


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_after_request_render_pushes_render_followed_by_still_render(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
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
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_when_schedule_render_called_before_still_render_keeps_animating(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
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
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_if_no_render_is_scheduled_doesnt_push(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )

    try:
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 0
    finally:
        await scheduler.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("encoder", list(RcaEncoder))
async def test_groups_close_request_render_together(
    encoder,
    a_threed_view,
):
    a_mock_push = MagicMock()
    scheduler = RcaRenderScheduler(
        a_mock_push,
        a_threed_view.render_window(),
        target_fps=20,
        interactive_quality=0,
        rca_encoder=encoder,
    )

    try:
        for _ in range(30):
            await scheduler.async_schedule_render()
        await asyncio.sleep(2)
        assert a_mock_push.call_count == 2
    finally:
        await scheduler.close()
