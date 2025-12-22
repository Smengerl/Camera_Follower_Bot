import time
import pytest

from camera_follower_bot import serial_manager as sm


class DummySerialOK:
    def __init__(self, *args, **kwargs):
        self.is_open = True

    def write(self, data):
        # pretend to write successfully
        self._last = data

    def close(self):
        self.is_open = False


class DummySerialFail:
    def __init__(self, *args, **kwargs):
        raise RuntimeError("port error")


def test_connect_success(monkeypatch):
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialOK}))
    mgr = sm.SerialManager(min_backoff=0.1, max_backoff=1.0)
    assert mgr.connect() is True
    assert mgr.is_connected() is True


def test_connect_failure(monkeypatch):
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    before = time.time()
    assert mgr.connect() is False
    assert mgr.ser is None
    assert mgr.attempt_count == 1
    # next_attempt_time should be in the future
    assert mgr.next_attempt_time >= before


def test_write_handles_exception_and_schedules_reconnect(monkeypatch):
    # First connect returns object whose write raises
    class WFail:
        def __init__(self, *a, **kw):
            pass

        def write(self, data):
            raise RuntimeError('write failed')

        def close(self):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': WFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    # connect succeeds (constructor returns instance)
    assert mgr.connect() is True
    # attempt to write data -> write() should return False and schedule reconnect
    ok = mgr.write(b'1,2\n')
    assert ok is False
    assert mgr.ser is None
    assert mgr.attempt_count >= 1


def test_send_position_formats_and_writes(monkeypatch):
    written = {}

    class WGood:
        def __init__(self, *a, **kw):
            pass

        def write(self, data):
            written['data'] = data

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': WGood}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    ok = mgr.send_position(10, -5)
    assert ok is True
    assert written['data'] == b'10,-5\n'
