import serial
import time
import logging

class DirectionSystem:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, debug=False):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)  # Wait for Arduino to reset
        self.debug = debug

    def map_power_to_duty(self, power):
        try:
            s = str(power).strip()
            p = float(s)
            p = max(-1.0, min(1.0, p))  # Clamp to [-1, 1]
            duty = int(p * 100)
            if self.debug:
                logging.info(f"map_power_to_duty: input={power}, stripped={s}, clamped={p}, duty={duty}")
            return duty
        except Exception as e:
            if self.debug:
                logging.error(f"map_power_to_duty error: {e}, input={power}")
            return 0

    def set_speed_left(self, power):
        speed = self.map_power_to_duty(power)
        if self.debug:
            logging.info(f'power left: {power}')
            logging.info(f'speed left: {speed}')
        cmd = f'L:{speed}\n'
        self.ser.write(cmd.encode('utf-8'))

    def set_speed_right(self, power):
        speed = self.map_power_to_duty(power)
        if self.debug:
            logging.info(f'power right: {power}')
            logging.info(f'speed right: {speed}')
        cmd = f'R:{speed}\n'
        self.ser.write(cmd.encode('utf-8'))

    def stop(self):
        self.ser.write(b'STOP\n')

    def close(self):
        self.ser.close()
   
   