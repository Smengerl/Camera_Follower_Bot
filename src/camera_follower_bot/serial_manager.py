import serial
import time
from collections import deque

# ---------------------------
# Configuration / constants
# ---------------------------
SERIAL_PORT = '/dev/cu.usbmodem101'
SERIAL_BAUD = 115200
DEFAULT_STDOUT_BUFFER_SIZE = 100  # Number of lines to keep in stdout buffer

class SerialManager:
    """Manage a serial connection with non-blocking exponential backoff reconnects.

    Usage: create an instance, call `reconnect_if_needed()` each main loop
    iteration and use `send_position(error_x,error_y)` to send payloads.
    The manager will silently drop sends when disconnected and attempt
    reconnects in the background (timed checks), avoiding blocking the
    main camera loop.
    
    Stdout tunneling: call `read_stdout()` to read available output from the
    device. The output is buffered internally and can be retrieved via
    `get_stdout_buffer()`.
    """

    def __init__(self, port: str = SERIAL_PORT, baud: int = SERIAL_BAUD, timeout: float = 1.0,
                 min_backoff: float = 0.5, max_backoff: float = 30.0,
                 stdout_buffer_size: int = DEFAULT_STDOUT_BUFFER_SIZE,
                 forward_serial_stdio: bool = False):
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

        # stdout buffering
        self.stdout_buffer_size = stdout_buffer_size
        self.stdout_buffer = deque(maxlen=stdout_buffer_size)
        self._partial_line = ""

        # Tunnel serial to stdio
        self.forward_serial_stdio = forward_serial_stdio

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
        if self.ser is None:
            return False
        try:
            self.ser.write(data)
            if self.forward_serial_stdio:
                print(f"Write: {data.decode().strip()}")
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


    
    @staticmethod
    def encode_line(error_x, error_y):
        """Format positional data as bytes."""
        try:
            return f"{int(error_x)},{int(error_y)}\n"
        except Exception:
            return None

    def send_position(self, error_x, error_y):
        """Format and send positional data if connected; otherwise do nothing."""
        data = SerialManager.encode_line(error_x, error_y)
        if data is None:
            return False
        return self.write(data.encode('utf-8'))
    
    def read_stdout(self):
        """Read available stdout from the serial device and buffer it.
        Also, if tunnel_stdio is enabled, forward received data to stdin.
        Returns True if data was read successfully, False otherwise.
        """
        if not self.is_connected():
            return False
        if self.ser is None:
            return False

        try:
            # Read all available bytes without blocking
            if self.ser.in_waiting > 0:
                data = self.ser.read(self.ser.in_waiting)
                decoded = data.decode('utf-8', errors='replace')

                # Combine with any partial line from previous read
                decoded = self._partial_line + decoded

                # Split into lines
                lines = decoded.split('\n')

                # Last element might be incomplete line
                self._partial_line = lines[-1]

                # Add complete lines to buffer
                for line in lines[:-1]:
                    # Skip empty and whitespace-only lines
                    if line.strip():
                        self.stdout_buffer.append(line.rstrip('\r'))

                        # Forward to stdout if enabled
                        if self.forward_serial_stdio:
                            print(f"Read: {line}")

                return True
            return False
        except Exception as exc:
            # On read error, mark disconnected and schedule reconnect
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
    
    def get_stdout_buffer(self, max_lines=None):
        """Get the current stdout buffer contents.
        
        Args:
            max_lines: Maximum number of recent lines to return. If None, returns all.
            
        Returns:
            List of stdout lines (strings), most recent last.
        """
        if max_lines is None:
            return list(self.stdout_buffer)
        else:
            # Return the most recent max_lines
            return list(self.stdout_buffer)[-max_lines:]
    
    def clear_stdout_buffer(self):
        """Clear the stdout buffer."""
        self.stdout_buffer.clear()
        self._partial_line = ""
    
    def send_relax_command(self, timeout: float = 1.0):
        """Send RELAX command to microcontroller and wait for acknowledgment.
        
        Args:
            timeout: Maximum time to wait for acknowledgment in seconds.
            
        Returns:
            True if acknowledgment received, False otherwise.
        """
        if not self.is_connected():
            return False
        
        # Clear buffer before sending to avoid false positives from old data
        initial_buffer_len = len(self.stdout_buffer)
        
        # Send RELAX command
        if not self.write(b'RELAX\n'):
            return False
        
        # Wait for acknowledgment
        start_time = time.time()
        while (time.time() - start_time) < timeout:
            # Read available data
            if self.read_stdout():
                # Check only new lines added since we started
                stdout_lines = self.get_stdout_buffer()
                for line in stdout_lines[initial_buffer_len:]:
                    if line.strip() == 'ACK_RELAX':
                        print(f"Servo relaxation confirmed: {line}")
                        return True
            
            # Small sleep to avoid busy-waiting
            time.sleep(0.01)
        
        # Timeout reached without acknowledgment
        print("Warning: Servo relaxation acknowledgment not received within timeout")
        return False
    
    def close(self):
        """Close the serial connection gracefully.
        
        Attempts to send RELAX command before closing.
        """
        if self.is_connected() and self.ser is not None:
            # Try to relax servos before closing
            self.send_relax_command(timeout=1.0)
            
            # Close the connection
            try:
                self.ser.close()
            except Exception:
                pass
            
            self.ser = None
