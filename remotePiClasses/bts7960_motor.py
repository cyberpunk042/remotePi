 # bts7960_motor.py
"""
Lightweight BTS-7960 motor wrapper for Raspberry Pi GPIO PWM.

Usage example
-------------
from bts7960_motor import BTS7960Motor
import time

motor = BTS7960Motor(pwm_right_pin=18, pwm_left_pin=19)  # BCM numbering
motor.setup()

motor.set_target_speed(80)     # ramp up to 80 % duty-cycle forward
for _ in range(100):           # call in your main loop / timer interrupt
    motor.update_speed()
    time.sleep(0.02)

motor.stop()
motor.cleanup()
"""

import RPi.GPIO as GPIO


class BTS7960Motor:
    def __init__(self, pwm_right_pin: int, pwm_left_pin: int, freq_hz: int = 1000):
        self._pwm_pin_right = pwm_right_pin
        self._pwm_pin_left = pwm_left_pin
        self._freq = freq_hz

        self.current_speed: int = 0   # −100 ↔ 100   (duty-cycle %)
        self._target_speed: int = 0

        self._pwm_right = None
        self._pwm_left = None

    # ---------- private helpers ---------- #
    def _write_speed(self, speed: int) -> None:
        """Translate signed speed (−100..100) to two PWM duty-cycles."""
        speed = max(-100, min(100, speed))  # clamp

        if speed >= 0:
            self._pwm_right.ChangeDutyCycle(speed)
            self._pwm_left.ChangeDutyCycle(0)
        else:
            self._pwm_right.ChangeDutyCycle(0)
            self._pwm_left.ChangeDutyCycle(-speed)

    # ---------- public API ---------- #
    def setup(self) -> None:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self._pwm_pin_right, GPIO.OUT)
        GPIO.setup(self._pwm_pin_left, GPIO.OUT)

        self._pwm_right = GPIO.PWM(self._pwm_pin_right, self._freq)
        self._pwm_left = GPIO.PWM(self._pwm_pin_left, self._freq)
        self._pwm_right.start(0)
        self._pwm_left.start(0)

    def set_target_speed(self, speed: int) -> None:
        """Speed in range −100..100 (negative = reverse)."""
        self._target_speed = max(-100, min(100, speed))

    def update_speed(self, step: int = 1) -> None:
        """
        Call periodically to slewrate toward target.
        `step` sets acceleration (1 → ~100 ms/100 steps at 10 kHz loop).
        """
        if self.current_speed < self._target_speed:
            self.current_speed = min(self.current_speed + step, self._target_speed)
        elif self.current_speed > self._target_speed:
            self.current_speed = max(self.current_speed - step, self._target_speed)

        self._write_speed(self.current_speed)

    def stop(self) -> None:
        self._target_speed = 0
        self.current_speed = 0
        self._write_speed(0)

    def cleanup(self) -> None:
        """Graceful GPIO teardown—call once when exiting."""
        self.stop()
        if self._pwm_right:
            self._pwm_right.stop()
        if self._pwm_left:
            self._pwm_left.stop()
        GPIO.cleanup()
