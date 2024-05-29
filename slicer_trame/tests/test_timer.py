from time import sleep
from unittest.mock import MagicMock

from slicer_trame.app.timer import Timer


def test_timer_timeout_calls_registered_callback():
    mock = MagicMock()

    timer = Timer()
    timer.addTimeoutCallback(mock)
    timer.setSingleShot(True)
    ten_ms = 10
    timer.setInterval(ten_ms)
    timer.start()

    sleep(1.0)

    mock.assert_called_once()


def test_timer_doesnt_call_unregistered_callback():
    timer = Timer()
    mock = MagicMock()
    timer.addTimeoutCallback(mock)
    timer.removeTimeoutCallback(mock)
    timer.setSingleShot(True)
    ten_ms = 10
    timer.setInterval(ten_ms)
    timer.start()

    sleep(1.0)

    mock.assert_not_called()


def test_timer_not_single_shot_calls_callbacks_multiple_times():
    timer = Timer()
    mock = MagicMock()
    timer.addTimeoutCallback(mock)
    timer.setSingleShot(False)
    ten_ms = 10
    timer.setInterval(ten_ms)
    timer.start()

    sleep(1.0)
    assert mock.call_count > 10


def test_starting_timer_multiple_times_runs_only_once():
    timer = Timer()
    mock = MagicMock()
    timer.addTimeoutCallback(mock)
    timer.setSingleShot(True)
    ten_ms = 10
    timer.setInterval(ten_ms)

    for _ in range(50):
        timer.start()

    sleep(1.0)
    mock.assert_called_once()
