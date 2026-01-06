import time
import random

from remote_logger import get_remote_logger
logger = get_remote_logger(__name__)

    
from input_reader import InputReader
from machine import Pin, PWM

# --- Configuration ---
DEADZONE_EYE = 25 # Beyond this threshold of target movement from center position, eye servos will move
DEADZONE_NECK = 20 # Beyond this threshold of eye movement from center position, a neck movement is triggered
NECK_DELAY_MS = 1200 # Minimum wait time between two neck moves (ms)
NECK_EYES_HOR_TRANSLATION = 1.25
NECK_EYES_VER_TRANSLATION = 0.6
KP = 0.03

CYCLE_TIME_S = 0.1  # Main loop min cycle time (s)

MIN_BLINK_WAIT_MS = 1000 # Minimum wait time between two blinks (ms)
MAX_BLINK_WAIT_MS = 5000 # Maximum wait time between two blinks (ms)
BLINK_TIME_S = 0.2  # Time eyelids stay closed during blink (s)

DISABLE_SLEEP_S = 0.5  # Sleep time when disabled
SWEEP_DELAY_S = 1.0  # Delay between servo sweeps (s)


LID_SYNC_OFFSET = -30  # Offset to keep eyelids slightly more closed than eye vertical position
NECK_SPEED_DEG_PER_S=60 # Speed of neck movement in degrees per second

SERVO_FREQUENCY_HZ = 50  # Standard servo frequency
SERVO_MIN_US = 544.0
SERVO_MAX_US = 2400.0
SERVO_RANGE_DEG = 180.0



# Compatibility for time.monotonic() in MicroPython
try:
    # MicroPython
    monotonic_ms = time.ticks_ms
except AttributeError:
    # CPython
    import time as _time
    monotonic_ms = lambda: int(_time.monotonic() * 1000)


# Simple replacement for Mode Enum
class Mode:
    HOLD = 0
    AUTO = 1


class Hardware:
    """Encapsulates hardware pins and servos."""

    def __init__(self):
        # switches
        self.enable = Pin(6, Pin.IN, Pin.PULL_UP)
        self.mode = Pin(7, Pin.IN, Pin.PULL_UP)
        self.blink_pin = Pin(9, Pin.IN, Pin.PULL_UP)
        self.led = Pin(25, Pin.OUT)

    def get_mode(self):
        # Return Mode.HOLD if self.mode.value() == False, else Mode.AUTO
        return Mode.HOLD if not self.mode.value() else Mode.AUTO

    def is_enabled(self):
        return self.enable.value()

    def led_flash(self, times=4, interval=0.2):
        logger.debug(f"LED flash {times} times with interval {interval}s")
        for _ in range(times):
            self.led.value(True)
            time.sleep(interval)
            self.led.value(False)
            time.sleep(interval)

    def led_trigger(self):
        self.led.value(not self.led.value())

# Servo configuration class
class ServoConfig:
    def __init__(self, pin, min_pos, max_pos, default):
        self.min = min_pos
        self.max = max_pos
        self.default = default
        self.target = default
        self.pin = Pin(pin)
        
        self.pwm = PWM(self.pin)
        self.pwm.freq(SERVO_FREQUENCY_HZ)  # Standard servo frequency
        

    def write(self, angle):
        """Write angle to servo, respecting min/max limits."""
        # ensure lo <= hi
        lo = self.min
        hi = self.max
        if lo > hi:
            lo, hi = hi, lo

        # Make sure angle is within bounds
        angle = min(max(lo, angle), hi)
    
        #self.servo.write(angle)
        

        current_us = angle / SERVO_RANGE_DEG * (SERVO_MAX_US - SERVO_MIN_US) + SERVO_MIN_US
        self.pwm.duty_ns(int(current_us * 1000.0))

        #logger.debug(f"Servo on pin {self.pin} set to angle {angle} (limits: {lo}-{hi}) = {current_us}us pulse")

        self.target = angle

    def calibrate(self):
        """Move servo to default position."""
        self.write(self.default)
        logger.debug(f"Servo on pin {self.pin} calibrated to default position {self.default}")

    def relax(self):
        """Deactivate servo PWM signal."""
        self.pwm.deinit()
        logger.debug(f"Servo on pin {self.pin} relaxed")

    def move_to_target(self, error, kp, deadzone):
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

        logger.debug(f"Moving servo on pin {self.pin} by step {step} for error {error} (adj: {adj})")
        
        new_target = self.target + step
        self.write(new_target)
        return True



class ServoController:
    """Manages servo targets, limits and movements."""


    def __init__(self):
        self.last_update = monotonic_ms()

        # helper values for smooth neck movement
        self.neck_hor_target = 90
        self.neck_ver_target = 90

        # servos
        self.servo_eyes_hor = ServoConfig(pin=10, min_pos=40, max_pos=140, default=90)
        self.servo_eyes_ver = ServoConfig(pin=11, min_pos=40, max_pos=140, default=90)
        self.servo_left_lid = ServoConfig(pin=12, min_pos=90, max_pos=170, default=90)
        self.servo_right_lid = ServoConfig(pin=14, min_pos=90, max_pos=10, default=90)
        self.servo_neck_hor = ServoConfig(pin=13, min_pos=10, max_pos=170, default=90)
        self.servo_neck_ver = ServoConfig(pin=15, min_pos=40, max_pos=140, default=90)

    def calibrate(self):
        """Calibrate all servos to default position (e.g. in hold mode)."""
        logger.info("Calibrate all servos")
        self.servo_eyes_hor.calibrate()
        self.servo_eyes_ver.calibrate()
        self.servo_left_lid.calibrate()
        self.servo_right_lid.calibrate()
        self.servo_neck_hor.calibrate()
        self.servo_neck_ver.calibrate()

    def relax(self):
        """Relax all servos to their default position."""
        logger.info("Relax all servos")
        self.servo_eyes_hor.relax()
        self.servo_eyes_ver.relax()
        self.servo_left_lid.relax()
        self.servo_right_lid.relax()
        self.servo_neck_hor.relax()
        self.servo_neck_ver.relax()

    def move_eyes(self, x_error, y_error):
        """Move eye servos based on x and y error values."""
        logger.info(f"Move eyes: x-error: {-x_error} / y-error: {y_error}")
        self.servo_eyes_hor.move_to_target(-x_error, KP, DEADZONE_EYE)
        self.servo_eyes_ver.move_to_target(y_error, KP, DEADZONE_EYE)

    def blink_eyes(self):
        """Perform a blink by moving eyelid servos to closed position"""
        logger.info("Blink eyes")
        self.servo_left_lid.write(self.servo_left_lid.min)
        self.servo_right_lid.write(self.servo_right_lid.min)

    def lid_sync(self):
        """Keep eyelid positions synced to vertical eye position."""
        # normalize UD position to range 0..1 (Blickhöhe)
        eyes_up_down_position_relative = (self.servo_eyes_ver.target - self.servo_eyes_ver.min) / (self.servo_eyes_ver.max - self.servo_eyes_ver.min)

        # compute target positions for lids based on UD position
        tl_target = int(self.servo_left_lid.max - ((self.servo_left_lid.max - self.servo_left_lid.min) * (0.5 * ( eyes_up_down_position_relative))) - LID_SYNC_OFFSET)
        tr_target = int(self.servo_right_lid.min + ((self.servo_right_lid.max - self.servo_right_lid.min) * (0.5 * (1 - eyes_up_down_position_relative))) + LID_SYNC_OFFSET)

        #print(f"Lid sync targets: Left: {tl_target} ({self.servo_left_lid.min}-{self.servo_left_lid.max}), Right: {tr_target} ({self.servo_right_lid.min}-{self.servo_right_lid.max})"
        #      f", Relative: {eyes_up_down_position_relative}")
        self.servo_left_lid.write(tl_target)
        self.servo_right_lid.write(tr_target)

        # 140 = 170 - (170-90) * 0.5 * x     -10 = 140 (x=0.5)
        # 80  = 90  + (10-90)  * 0.5 * (1-x) +10 = 80  (x=0.5)

    def neck_target(self):
        """Map eye movement (LR/UD) to base targets (but do not yet move the base); tweak multipliers as needed."""
        logger.info("Move neck")
        self.neck_hor_target = int(self.servo_eyes_hor.target * NECK_EYES_HOR_TRANSLATION)
        self.neck_ver_target = int(90 - ((90 - self.servo_eyes_ver.target) * NECK_EYES_VER_TRANSLATION))

    def neck_smooth_move(self, speed_deg_per_s=NECK_SPEED_DEG_PER_S):
        """Smoothly move neck servos towards target positions."""
        now = monotonic_ms()
        dt = now - self.last_update
        self.last_update = now
        if dt <= 0:
            return

        step_size = speed_deg_per_s * dt / 1000.0  # degrees to move this update

        # BaseX
        bx = float(self.servo_neck_hor.target)
        bx_target = float(self.neck_hor_target)
        dx = bx_target - bx
        if abs(dx) <= step_size:
            bx = bx_target
        else:
            bx += step_size if dx > 0 else -step_size
        self.servo_neck_hor.write(int(round(bx)))

        # BaseY
        by = float(self.servo_neck_ver.target)
        by_target = float(self.neck_ver_target)
        dy = by_target - by
        if abs(dy) <= step_size:
            by = by_target
        else:
            by += step_size if dy > 0 else -step_size
        self.servo_neck_ver.write(int(round(by)))


    def sweep(self):
        logger.info("Sweep all servos")
        self.calibrate()

        logger.info("Neck Horizontal Sweep Test")
        self.servo_neck_hor.write(self.servo_neck_hor.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_neck_hor.write(self.servo_neck_hor.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_neck_hor.calibrate()

        logger.info("Neck Vertical Sweep Test")
        self.servo_neck_ver.write(self.servo_neck_ver.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_neck_ver.write(self.servo_neck_ver.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_neck_ver.calibrate()

        logger.info("Left Lid Sweep Test")
        self.servo_left_lid.write(self.servo_left_lid.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_left_lid.write(self.servo_left_lid.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_left_lid.calibrate()

        logger.info("Right Lid Sweep Test")
        self.servo_right_lid.write(self.servo_right_lid.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_right_lid.write(self.servo_right_lid.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_right_lid.calibrate()

        logger.info("Eyes Sweep Test")
        self.servo_eyes_ver.write(self.servo_eyes_ver.min)
        self.servo_eyes_hor.write(self.servo_eyes_hor.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_eyes_ver.write(self.servo_eyes_ver.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_eyes_hor.write(self.servo_eyes_hor.max)
        time.sleep(SWEEP_DELAY_S)
        self.servo_eyes_ver.write(self.servo_eyes_ver.min)
        time.sleep(SWEEP_DELAY_S)
        self.servo_eyes_ver.calibrate()
        self.servo_eyes_hor.calibrate()




def main():
    hw = Hardware()
    controller = ServoController()
    reader = InputReader()

    # initial state
    neck_flag = False
    neck_trigger_time = 0
    blink_trigger_time = 0

    # quick LED flash on start to indicate boot
    hw.led_flash(times=2, interval=0.12)

    logger.info("Starting main loop")
    try:
        # main loop
        while True:
            cycle_start = monotonic_ms()
            mode = hw.get_mode()
            if mode == Mode.HOLD:
                controller.sweep()
            elif mode == Mode.AUTO:
                # auto mode
                if hw.is_enabled():
                    read_line = reader.read_latest()
                    if read_line is not None:
                        (x_err, y_err, relax_cmd) = read_line

                        if relax_cmd is not None and relax_cmd:
                            logger.info("ACK_RELAX received, exiting main loop")
                            break
                        elif x_err is not None and y_err is not None:
                            logger.debug(f"Received position error: {x_err},{y_err}")
                            # move eyes/eyelids
                            controller.move_eyes(x_err, y_err)

                    # random blink
                    if (blink_trigger_time == 0) or (monotonic_ms() > blink_trigger_time):
                        blink_trigger_time = monotonic_ms() + MIN_BLINK_WAIT_MS + random.randint(0, MAX_BLINK_WAIT_MS - MIN_BLINK_WAIT_MS)
                        controller.blink_eyes()
                        time.sleep(BLINK_TIME_S)

                    # keep lids synced to UD position
                    controller.lid_sync()

                    # decide if neck should move
                    if (
                        abs(controller.servo_eyes_ver.target - controller.servo_eyes_ver.default) >= DEADZONE_NECK
                        or abs(controller.servo_eyes_hor.target - controller.servo_eyes_hor.default) >= DEADZONE_NECK
                    ):
                        if not neck_flag:
                            neck_trigger_time = monotonic_ms()
                            neck_flag = True

                        if neck_flag and (monotonic_ms() - neck_trigger_time) >= NECK_DELAY_MS:
                            controller.neck_target()
                            neck_flag = False

                    controller.neck_smooth_move()

                    elapsed_ms = monotonic_ms() - cycle_start
                    wait_s = max(0, CYCLE_TIME_S - (elapsed_ms / 1000.0))
                    if wait_s > 0:
                        time.sleep(wait_s)
                    hw.led_trigger()
                else:
                    logger.info("Disabled")
                    time.sleep(DISABLE_SLEEP_S)
    except Exception as e:
        logger.exception(f"Uncaught exception in main loop: {e}")
    finally:
        logger.info("Main loop ended, relaxing servos")
        controller.relax()  


if __name__ == "__main__":
    main()
