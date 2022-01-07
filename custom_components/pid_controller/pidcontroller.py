#
#  Copyright (c) 2022, Diogo Silva "Soloam"
#  Creative Commons BY-NC-SA 4.0 International Public License
#  (see LICENSE.md or https://creativecommons.org/licenses/by-nc-sa/4.0/)
#
"""
PID Controller.
For more details about this sensor, please refer to the documentation at
https://github.com/soloam/ha-pid-controller/
"""
import time


class PIDController:
    """PID Controller"""

    def __init__(self, P=0.2, I=0.0, D=0.0, current_time=None):
        self._p = 0
        self._i = 0
        self._d = 0

        self._kp = P
        self._ki = I
        self._kd = D

        self._sample_time = 0.00
        self._current_time = current_time if current_time is not None else time.time()
        self._last_time = self._current_time

        self._p_term = 0
        self._i_term = 0
        self._d_term = 0

        self._output = 0

        self._windup = 0

        self._last_error = 0

        self.reset()

    def reset(self):
        self._set_point = 0.0

        self._p = 0
        self._i = 0
        self._d = 0

        self._p_term = 0.0
        self._i_term = 0.0
        self._d_term = 0.0
        self._last_error = 0.0

        # Windup Guard
        self._windup = 20.0

        self._output = 0.0

    def reset_pid(self):
        self._p_term = 0
        self._i_term = 0
        self._d_term = 0

        self._last_error = 0
        self._last_time = 0

    def update(self, feedback_value, current_time=None):
        """Calculates PID value for given reference feedback"""
        error = self._set_point - feedback_value

        self._current_time = current_time if current_time is not None else time.time()
        delta_time = self._current_time - self._last_time
        delta_error = error - self._last_error

        if delta_time >= self._sample_time:
            self._p_term = self._kp * error
            self._i_term += error * delta_time

            if self._i_term < -self._windup:
                self._i_term = -self._windup
            elif self._i_term > self._windup:
                self._i_term = self._windup

            self._d_term = 0.0
            if delta_time > 0:
                self._d_term = delta_error / delta_time

            # Remember last time and last error for next calculation
            self._last_time = self._current_time
            self._last_error = error

            self._p = self._p_term
            self._i = self._ki * self._i_term
            self._d = self._kd * self._d_term

            self._output = self._p + self._i + self._d

    @property
    def kpg(self):
        """Aggressively the PID reacts to the current error with setting Proportional Gain"""
        return self._kp

    @kpg.setter
    def kpg(self, value):
        self._kp = value

    @property
    def kig(self):
        """Aggressively the PID reacts to the current error with setting Integral Gain"""
        return self._ki

    @kig.setter
    def kig(self, value):
        self._ki = value

    @property
    def kdg(self):
        """Determines how aggressively the PID reacts to the current
        error with setting Derivative Gain"""
        return self._kd

    @kdg.setter
    def kdg(self, value):
        self._kd = value

    @property
    def set_point(self):
        """The target point to the PID"""
        return self._set_point

    @set_point.setter
    def set_point(self, value):
        self._set_point = value

    @property
    def windup(self):
        """Integral windup, also known as integrator windup or reset windup,
        refers to the situation in a PID feedback controller where
        a large change in setpoint occurs (say a positive change)
        and the integral terms accumulates a significant error
        during the rise (windup), thus overshooting and continuing
        to increase as this accumulated error is unwound
        (offset by errors in the other direction).
        The specific problem is the excess overshooting.
        """
        return self._windup

    @windup.setter
    def windup(self, value):
        self._windup = value

    @property
    def sample_time(self):
        """PID that should be updated at a regular interval.
        Based on a pre-determined sampe time, the PID decides if it should compute or
        return immediately.
        """
        return self._sample_time

    @sample_time.setter
    def sample_time(self, value):
        self._sample_time = value

    @property
    def p(self):  # pylint: disable=invalid-name
        return self._p

    @property
    def i(self):
        return self._i

    @property
    def d(self):  # pylint: disable=invalid-name
        return self._d

    @property
    def output(self):
        """PID result"""
        return self._output
