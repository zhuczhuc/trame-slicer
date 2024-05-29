import threading
from typing import Optional


class Timer:
    """
    Timer implementation for periodic actions.
    Equivalent API to QTimer.
    """

    def __init__(self, isSingleShot=False, interval_ms=0, timeoutCallbacks=None):
        self.interval_ms = interval_ms
        self.isSingleShot = isSingleShot
        self.timeoutCallbacks = timeoutCallbacks or set()
        self.thread: Optional[threading.Timer] = None

    def __del__(self):
        self.stop()

    def setInterval(self, interval_ms):
        self.interval_ms = interval_ms

    def setSingleShot(self, isSingleShot):
        self.isSingleShot = isSingleShot

    def addTimeoutCallback(self, callback):
        self.timeoutCallbacks.add(callback)

    def removeTimeoutCallback(self, callback):
        self.timeoutCallbacks.remove(callback)

    def _timeOut(self):
        if self.isSingleShot:
            self.thread = None

        if self.thread:
            self._start_next()

        for callback in self.timeoutCallbacks:
            callback()

    def start(self, interval_ms=-1):
        if interval_ms >= 0:
            self.interval_ms = interval_ms

        self._start_next()

    def stop(self):
        if not self.thread:
            return

        self.thread.cancel()
        self.thread = None

    def _start_next(self):
        self.stop()
        self.thread = threading.Timer(self.interval_ms / 1000., self._timeOut)
        self.thread.daemon = True
        self.thread.start()
