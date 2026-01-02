import pytest
from camera_follower_bot.serial_manager import SerialManager
from rpi_pico_code.input_reader import InputReader

@pytest.mark.parametrize("line,expected", [
    ((12, -7), "12,-7\n"),
    ((0, 0), "0,0\n"),
    ((-5, 10), "-5,10\n"),
    ((-5, None), None),
    ((None, 10), None),
    ((None, None), None),
])
def test_encode_static(line, expected):
    encoded = SerialManager.encode_line(line[0], line[1]) 
    assert encoded == expected


@pytest.mark.parametrize("line,expected", [
    ("12,-7\n", (12, -7, False)),
    ("0,0\n", (0, 0, False)),
    ("-5,10\n", (-5, 10, False)),
    ("badline\n", (None, None, None)),
    ("-5,10", (-5, 10, False)),
    ("3,", (None, None, None)),
    ("2", (None, None, None)),
    ("", (None, None, None)),
    ("RELAX\n", (None, None, True)),
    ("RELAX", (None, None, True)),
    ("  RELAX  \n", (None, None, True)),
])
def test_decode_static(line, expected):
    decoded = InputReader.decode_line(line)
    if (expected is None):
        assert decoded == (None, None, None)
    assert decoded == expected


import random

@pytest.mark.parametrize("line", [
    (random.randint(-1000, 1000), random.randint(-1000, 1000), False)
    for _ in range(100)
])
def test_decode_encode_static(line):
    encoded = SerialManager.encode_line(line[0], line[1])
    # decode_line expects a string, so decode bytes
    decoded = InputReader.decode_line(encoded)
    assert decoded == line
