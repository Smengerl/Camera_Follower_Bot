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


def test_read_stdout_when_not_connected(monkeypatch):
    """Test that read_stdout returns False when not connected."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    assert mgr.connect() is False
    result = mgr.read_stdout()
    assert result is False


def test_read_stdout_with_no_data(monkeypatch):
    """Test that read_stdout returns False when no data is available."""
    class SerialNoData:
        def __init__(self, *a, **kw):
            self.is_open = True
            self.in_waiting = 0

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialNoData}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    result = mgr.read_stdout()
    assert result is False


def test_read_stdout_with_single_line(monkeypatch):
    """Test reading a single complete line from stdout."""
    class SerialWithData:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._data = b'Hello World\n'

        @property
        def in_waiting(self):
            return len(self._data)

        def read(self, size):
            data = self._data[:size]
            self._data = self._data[size:]
            return data

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithData}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    result = mgr.read_stdout()
    assert result is True
    buffer = mgr.get_stdout_buffer()
    assert len(buffer) == 1
    assert buffer[0] == 'Hello World'


def test_read_stdout_with_multiple_lines(monkeypatch):
    """Test reading multiple lines from stdout."""
    class SerialWithMultipleLines:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._data = b'Line 1\nLine 2\nLine 3\n'

        @property
        def in_waiting(self):
            return len(self._data)

        def read(self, size):
            data = self._data[:size]
            self._data = self._data[size:]
            return data

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithMultipleLines}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    result = mgr.read_stdout()
    assert result is True
    buffer = mgr.get_stdout_buffer()
    assert len(buffer) == 3
    assert buffer[0] == 'Line 1'
    assert buffer[1] == 'Line 2'
    assert buffer[2] == 'Line 3'


def test_read_stdout_with_partial_line(monkeypatch):
    """Test that partial lines are buffered correctly."""
    class SerialWithPartialLine:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._calls = 0

        @property
        def in_waiting(self):
            if self._calls == 0:
                return 10
            elif self._calls == 1:
                return 7
            return 0

        def read(self, size):
            self._calls += 1
            if self._calls == 1:
                return b'Hello Wor'
            elif self._calls == 2:
                return b'ld!\n'
            return b''

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithPartialLine}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    
    # First read gets partial line
    result1 = mgr.read_stdout()
    assert result1 is True
    buffer1 = mgr.get_stdout_buffer()
    assert len(buffer1) == 0  # No complete lines yet
    
    # Second read completes the line
    result2 = mgr.read_stdout()
    assert result2 is True
    buffer2 = mgr.get_stdout_buffer()
    assert len(buffer2) == 1
    assert buffer2[0] == 'Hello World!'


def test_read_stdout_handles_exception(monkeypatch):
    """Test that read_stdout handles exceptions and schedules reconnect."""
    class SerialReadFail:
        def __init__(self, *a, **kw):
            self.is_open = True
            self.in_waiting = 5

        def read(self, size):
            raise RuntimeError('read failed')

        def close(self):
            pass

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialReadFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    assert mgr.connect() is True
    result = mgr.read_stdout()
    assert result is False
    assert mgr.ser is None
    assert mgr.attempt_count >= 1


def test_get_stdout_buffer_with_max_lines(monkeypatch):
    """Test retrieving limited number of lines from buffer."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialOK}))
    mgr = sm.SerialManager(stdout_buffer_size=10)
    
    # Manually add lines to buffer for testing
    for i in range(5):
        mgr.stdout_buffer.append(f'Line {i}')
    
    # Get last 3 lines
    buffer = mgr.get_stdout_buffer(max_lines=3)
    assert len(buffer) == 3
    assert buffer[0] == 'Line 2'
    assert buffer[1] == 'Line 3'
    assert buffer[2] == 'Line 4'


def test_stdout_buffer_overflow(monkeypatch):
    """Test that buffer respects max size and drops old lines."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialOK}))
    mgr = sm.SerialManager(stdout_buffer_size=3)
    
    # Add more lines than buffer size
    for i in range(5):
        mgr.stdout_buffer.append(f'Line {i}')
    
    # Should only keep last 3
    buffer = mgr.get_stdout_buffer()
    assert len(buffer) == 3
    assert buffer[0] == 'Line 2'
    assert buffer[1] == 'Line 3'
    assert buffer[2] == 'Line 4'


def test_clear_stdout_buffer(monkeypatch):
    """Test clearing the stdout buffer."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialOK}))
    mgr = sm.SerialManager()
    
    # Add some lines
    mgr.stdout_buffer.append('Line 1')
    mgr.stdout_buffer.append('Line 2')
    mgr._partial_line = 'Partial'
    
    # Clear
    mgr.clear_stdout_buffer()
    
    assert len(mgr.stdout_buffer) == 0
    assert mgr._partial_line == ''


def test_read_stdout_with_carriage_return(monkeypatch):
    """Test that carriage returns are stripped properly."""
    class SerialWithCR:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._data = b'Line 1\r\nLine 2\r\n'

        @property
        def in_waiting(self):
            return len(self._data)

        def read(self, size):
            data = self._data[:size]
            self._data = self._data[size:]
            return data

        def write(self, data):
            pass

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithCR}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    result = mgr.read_stdout()
    assert result is True
    buffer = mgr.get_stdout_buffer()
    assert len(buffer) == 2
    assert buffer[0] == 'Line 1'
    assert buffer[1] == 'Line 2'


def test_send_relax_command_success(monkeypatch):
    """Test sending RELAX command and receiving acknowledgment."""
    class SerialWithRelaxAck:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._written = []
            self._response = b'ACK_RELAX\n'

        def write(self, data):
            self._written.append(data)

        @property
        def in_waiting(self):
            return len(self._response)

        def read(self, size):
            data = self._response[:size]
            self._response = self._response[size:]
            return data

        def close(self):
            self.is_open = False

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithRelaxAck}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    
    # Send RELAX command
    result = mgr.send_relax_command(timeout=0.5)
    assert result is True
    assert mgr.ser._written[0] == b'RELAX\n'


def test_send_relax_command_timeout(monkeypatch):
    """Test sending RELAX command without receiving acknowledgment."""
    class SerialNoAck:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._written = []

        def write(self, data):
            self._written.append(data)

        @property
        def in_waiting(self):
            return 0

        def read(self, size):
            return b''

        def close(self):
            self.is_open = False

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialNoAck}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    
    # Send RELAX command with very short timeout
    result = mgr.send_relax_command(timeout=0.1)
    assert result is False
    assert mgr.ser._written[0] == b'RELAX\n'


def test_send_relax_command_not_connected(monkeypatch):
    """Test sending RELAX command when not connected."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    assert mgr.connect() is False
    
    # Try to send RELAX command
    result = mgr.send_relax_command(timeout=0.5)
    assert result is False


def test_close_method_sends_relax(monkeypatch):
    """Test that close method sends RELAX command."""
    written_data = []
    
    class SerialWithRelaxAck:
        def __init__(self, *a, **kw):
            self.is_open = True
            self._response = b'ACK_RELAX\n'
            self._closed = False

        def write(self, data):
            written_data.append(data)

        @property
        def in_waiting(self):
            return len(self._response) if not self._closed else 0

        def read(self, size):
            if self._closed:
                return b''
            data = self._response[:size]
            self._response = self._response[size:]
            return data

        def close(self):
            self._closed = True
            self.is_open = False

    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': SerialWithRelaxAck}))
    mgr = sm.SerialManager()
    assert mgr.connect() is True
    
    # Close the manager
    mgr.close()
    
    # Verify RELAX was sent (captured in outer scope)
    assert len(written_data) > 0
    assert written_data[0] == b'RELAX\n'
    assert mgr.ser is None


def test_close_method_when_not_connected(monkeypatch):
    """Test that close method handles not being connected."""
    monkeypatch.setattr(sm, 'serial', type('X', (), {'Serial': DummySerialFail}))
    mgr = sm.SerialManager(min_backoff=0.01, max_backoff=0.02)
    assert mgr.connect() is False
    
    # Close should not raise an error
    mgr.close()
    assert mgr.ser is None
