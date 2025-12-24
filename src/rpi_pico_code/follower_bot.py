
import time
import random
from enum import Enum, auto

from input_reader import InputReader
from machine import Pin, ADC
from servo import Servo

# --- Configuration ---
DEADZONE_EYE = 25
DEADZONE_NECK = 20 # Beyond this threshold of eye movement from center position, a neck movement is triggered
NECK_DELAY_MS = 1200 # Minimum wait time between two neck moves (ms)
NECK_X_MAP = 1.25
NECK_Y_MAP = 1
KP = 0.03
BLINK_PROBABILITY_PER_FRAME = 1 / 60.0




#
class Mode(Enum):
    HOLD = auto()
    AUTO = auto()


class Hardware:
    """Encapsulates hardware pins and servos."""

    def __init__(self):
        # switches
        self.enable = Pin(6, Pin.IN, Pin.PULL_UP)
        self.mode = Pin(7, Pin.IN, Pin.PULL_UP)
        self.blink_pin = Pin(9, Pin.IN, Pin.PULL_UP)
        self.led = Pin(25, Pin.OUT)

        # analog inputs (currently unused but kept for reference)
        self.UD = ADC(26)
        self.trim = ADC(27)
        self.LR = ADC(28)

    def get_mode(self):
        # Return Mode.HOLD if self.mode.value() == False, else Mode.AUTO
        return Mode.HOLD if not self.mode.value() else Mode.AUTO

    def is_enabled(self):
        return not self.enable.value()

    def led_flash(self, times=4, interval=0.2):
        for _ in range(times):
            self.led.value(not self.led.value())
            time.sleep(interval)
        # ensure LED off at end
        self.led.value(0)


# Servo configuration class
class ServoConfig:
    def __init__(self, pin, min_pos, max_pos, default):
        self.min = min_pos
        self.max = max_pos
        self.default = default
        self.target = default
        self.servo = Servo(pin_id=pin)
        

    def write_servo(self, angle):
        """Write angle to servo, respecting min/max limits."""
        # ensure lo <= hi
        lo = self.min
        hi = self.max
        if lo > hi:
            lo, hi = hi, lo

        # Make sure angle is within bounds
        angle = max(lo, min(hi, angle))
    
        self.servo.write(angle)
        self.target = angle

    def calibrate(self):
        """Move servo to default position."""
        self.write_servo(self.default)


    def move_target(self, error, kp=KP, deadzone=DEADZONE_EYE):
        """Move a given servo target based on error and proportional control.

        Returns True if a movement occurred.
        """
        if abs(error) <= deadzone:
            return False

        # adjust error relative to deadzone
        if error > 0:
            adj = error - deadzone
        else:
            adj = error + deadzone

        step = int(kp * adj)
        if step == 0:
            step = 1 if adj > 0 else -1

        new_target = self.target + step
        self.write_servo(new_target)
        return True



class ServoController:
    """Manages servo targets, limits and movements."""


    def __init__(self):
        self.last_update = time.ticks_ms()

        # helper values for smooth neck movement
        self.bx_target = 90
        self.by_target = 90

        # servos
        self.servo_lr = ServoConfig(pin=10, min_pos=40, max_pos=140, default=90)
        self.servo_ud = ServoConfig(pin=11, min_pos=40, max_pos=140, default=90)
        self.servo_tl = ServoConfig(pin=12, min_pos=90, max_pos=170, default=90)
        self.servo_tr = ServoConfig(pin=14, min_pos=90, max_pos=10, default=90)
        self.servo_base_x = ServoConfig(pin=13, min_pos=10, max_pos=170, default=90)
        self.servo_base_y = ServoConfig(pin=15, min_pos=40, max_pos=140, default=90)

    def calibrate(self):
        """Calibrate all servos to default position (e.g. in hold mode)."""
        self.servo_lr.calibrate()
        self.servo_ud.calibrate()
        self.servo_tl.calibrate()
        self.servo_tr.calibrate()
        self.servo_base_x.calibrate()
        self.servo_base_y.calibrate()
        
    def move_eyes(self, x_error, y_error):
        """Move eye servos based on x and y error values."""
        self.servo_lr.move_target(-x_error)
        self.servo_ud.move_target(y_error)

    def blink_eyes(self):
        """Perform a blink by moving eyelid servos to closed position"""
        self.servo_tl.write_servo(self.servo_tl.default)
        self.servo_tr.write_servo(self.servo_tr.default)

    def lid_sync(self):
        """Keep eyelid positions synced to vertical eye position."""
        # normalize UD position to range 0..1 (Blickhöhe)
        ud_pos = (self.servo_ud.target - self.servo_ud.min) / (self.servo_ud.max - self.servo_ud.min)

        # compute target positions for TL and TR based on UD position
        tl_target = int(self.servo_tl.max - ((self.servo_tl.max - self.servo_tl.min) * (0.5 * (1 - ud_pos))) - 10)
        tr_target = int(self.servo_tr.min + ((self.servo_tr.max - self.servo_tr.min) * (0.5 * (1 - ud_pos))) + 10)

        self.servo_tl.write_servo(tl_target)
        self.servo_tr.write_servo(tr_target)

    def neck_target(self):
        """Map eye movement (LR/UD) to base targets (but do not yet move the base); tweak multipliers as needed."""
        self.bx_target = int(self.servo_lr.target * NECK_X_MAP)
        self.by_target = int(90 - ((90 - self.servo_ud.target) * 0.6))

    def neck_smooth_move(self, speed_deg_per_s=60):
        """Smoothly move neck servos towards target positions."""
        # Use time.monotonic() for CPython compatibility
        now = time.monotonic() * 1000  # ms
        dt = now - getattr(self, 'last_update', now)
        self.last_update = now

        if dt <= 0:
            return

        step_size = (speed_deg_per_s * dt) / 1000.0

        # BaseX
        bx = float(self.servo_base_x.target)
        bx_target = float(self.bx_target)
        dx = bx_target - bx
        if abs(dx) <= step_size:
            bx = bx_target
        else:
            bx += step_size if dx > 0 else -step_size
        self.servo_base_x.write_servo(int(round(bx)))

        # BaseY
        by = float(self.servo_base_y.target)
        by_target = float(self.by_target)
        dy = by_target - by
        if abs(dy) <= step_size:
            by = by_target
        else:
            by += step_size if dy > 0 else -step_size
        self.servo_base_y.write_servo(int(round(by)))

    




def main():
    hw = Hardware()
    controller = ServoController()
    reader = InputReader()

    # initial state
    neck_flag = False
    neck_trigger_time = 0

    # quick LED flash on start to indicate boot
    hw.led_flash(times=2, interval=0.12)

    # main loop
    while True:
        mode = hw.get_mode()
        if mode == Mode.HOLD:
            # calibration mode — center all servos
            controller.calibrate()
            time.sleep(0.5)
        elif mode == Mode.AUTO:
            # auto mode
            if hw.is_enabled():
                data = reader.read_latest()
                if data:
                    x_err, y_err = data
                    if x_err is not None and y_err is not None:
                        # move eyes/eyelids
                        controller.move_eyes(x_err, y_err)

                # random blink
                if random.random() < BLINK_PROBABILITY_PER_FRAME:
                    controller.blink_eyes()
                    time.sleep(0.06)

                # keep lids synced to UD position
                controller.lid_sync()

                # decide if neck should move
                if (
                    abs(controller.servo_ud.target - 90) >= DEADZONE_NECK
                    or abs(controller.servo_lr.target - 90) >= DEADZONE_NECK
                ):
                    if not neck_flag:
                        neck_trigger_time = time.monotonic() * 1000  # ms
                        neck_flag = True

                    if neck_flag and ((time.monotonic() * 1000) - neck_trigger_time) >= NECK_DELAY_MS:
                        controller.neck_target()
                        neck_flag = False

                controller.neck_smooth_move()

            # small sleep — tune as required
            time.sleep(0.001)


if __name__ == "__main__":
    main()
