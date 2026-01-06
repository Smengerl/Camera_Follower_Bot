import sys
import select
import logging

from remote_logger import get_remote_logger
logger = get_remote_logger(__name__)


class InputReader:
    """Non-blocking stdin reader that returns the latest x,y pair or None.
    
    Also handles special commands like 'RELAX' for servo control.
    """
    
    @staticmethod
    def decode_line(line) -> tuple[int | None, int | None, bool | None]:
        """Decode a line of positional data or a special command.
        Returns:
            - (x, y, False) when receiving valid positional data
            - (None, None, True) for relax command
            - (None, None, None) for invalid data
        """
        stripped = line.strip()
        # Check for special commands
        if stripped == "RELAX":
            logger.info("Received RELAX command from input.")
            return None, None, True
        # Try to decode as position data
        try:
            x_str, y_str = stripped.split(",")
            x, y = int(x_str), int(y_str)
            logger.debug(f"Decoded position from input: x={x}, y={y}")
            return x, y, False
        except Exception as e:
            logger.warning(f"Invalid input data: '{line.strip()}'. Error: {e}")
            return None, None, None

    @staticmethod
    def read_latest() -> tuple[int | None, int | None, bool | None]:
        """Read the latest line from stdin without blocking."""
        latest_line = None
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            latest_line = sys.stdin.readline()
            logger.debug(f"Read line from stdin: {latest_line.strip()}")

        if not latest_line:
            logger.debug("No input received from stdin.")
            return None, None, None

        return InputReader.decode_line(latest_line)
