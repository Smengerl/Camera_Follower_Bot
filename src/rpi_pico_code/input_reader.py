import sys
import select


class InputReader:
    """Non-blocking stdin reader that returns the latest x,y pair or None."""
    
    @staticmethod
    def decode_line(line):
        """Decode a line of positional data."""
        try:
            x_str, y_str = line.strip().split(",")
            return int(x_str), int(y_str)
        except Exception:
            return None, None

    @staticmethod
    def read_latest():
        latest_line = None
        while sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            latest_line = sys.stdin.readline()

        if not latest_line:
            return None

        return InputReader.decode_line(latest_line)
