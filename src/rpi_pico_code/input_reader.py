import sys
import select


class InputReader:
    """Non-blocking stdin reader that returns the latest x,y pair or None.
    
    Also handles special commands like 'RELAX' for servo control.
    """
    
    @staticmethod
    def decode_line(line) -> tuple[int | None, int | None, bool | None]:
        """Decode a line of positional data or a special command.
        
        Returns:
            - (x, y) tuple for position data
            - ('RELAX',) tuple for relax command
            - (None, None) for invalid data
        """
        stripped = line.strip()
        
        # Check for special commands
        if stripped == "RELAX":
            return None, None, True
        
        # Try to decode as position data
        try:
            x_str, y_str = stripped.split(",")
            return int(x_str), int(y_str), False
        except Exception:
            return None, None, None

    @staticmethod
    def read_latest() -> tuple[int | None, int | None, bool | None]:
        """Read the latest line from stdin without blocking."""
        latest_line = None
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            latest_line = sys.stdin.readline()

        if not latest_line:
            return None, None, None

        return InputReader.decode_line(latest_line)
