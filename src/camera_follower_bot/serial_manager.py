import serial
import time

# ---------------------------
# Configuration / constants
# ---------------------------
SERIAL_PORT = '/dev/cu.usbmodem101'
SERIAL_BAUD = 115200

class SerialManager:
    """Manage a serial connection with non-blocking exponential backoff reconnects.

    Usage: create an instance, call `reconnect_if_needed()` each main loop
    iteration and use `send_position(error_x,error_y)` to send payloads.
    The manager will silently drop sends when disconnected and attempt
    reconnects in the background (timed checks), avoiding blocking the
    main camera loop.
    """

    def __init__(self, port: str = SERIAL_PORT, baud: int = SERIAL_BAUD, timeout: float = 1.0,
                 min_backoff: float = 0.5, max_backoff: float = 30.0):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

        # backoff parameters
        self.min_backoff = min_backoff
        self.max_backoff = max_backoff
        self.attempt_count = 0
        self.next_attempt_time = 0.0
        self.last_error = None

    def connect(self):
        """Try to open the serial port once. Returns True if successful."""
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            # allow the device to reset
            time.sleep(2)
            self.attempt_count = 0
            self.next_attempt_time = 0.0
            self.last_error = None
            return True
        except Exception as exc:
            # schedule next attempt using exponential backoff
            self.ser = None
            self.last_error = exc
            self.attempt_count += 1
            backoff = min(self.min_backoff * (2 ** (self.attempt_count - 1)), self.max_backoff)
            self.next_attempt_time = time.time() + backoff
            return False

    def reconnect_if_needed(self):
        """If disconnected and backoff time passed, attempt reconnect."""
        if self.ser is None and time.time() >= self.next_attempt_time:
            self.connect()

    def is_connected(self) -> bool:
        return self.ser is not None and getattr(self.ser, 'is_open', True)

    def write(self, data: bytes):
        """Write bytes to serial port if connected. On failure, close and schedule reconnect."""
        if not data:
            return False
        if not self.is_connected():
            return False
        try:
            self.ser.write(data)
            return True
        except Exception as exc:
            # mark disconnected and schedule reconnect
            try:
                self.ser.close()
            except Exception:
                pass
            self.ser = None
            self.last_error = exc
            self.attempt_count += 1
            backoff = min(self.min_backoff * (2 ** (self.attempt_count - 1)), self.max_backoff)
            self.next_attempt_time = time.time() + backoff
            return False

    def send_position(self, error_x, error_y):
        """Format and send positional data if connected; otherwise do nothing."""
        try:
            data = f"{int(error_x)},{int(error_y)}\n"
        except Exception:
            return False
        return self.write(data.encode('utf-8'))
     
