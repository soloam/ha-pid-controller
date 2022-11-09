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

# pylint: disable=invalid-name


class PIDController:
    """PID Controller"""

    WARMUP_STAGE = 3

    def __init__(self, P=0.2, I=0.0, D=0.0, logger=None):
        self._logger = logger

        self._set_point = 0
        self._windup = (None, None)
        self._output = 0.0

        self._kp = P
        self._ki = I
        self._kd = D

        self._p_term = 0.0
        self._i_term = 0.0
        self._d_term = 0.0

        self._sample_time = None
        self._last_output = None
        self._last_input = None
        self._last_time = None

        self.reset_pid()

    def reset_pid(self):
        self._p_term = 0.0
        self._i_term = 0.0
        self._d_term = 0.0

        self._sample_time = None
        self._last_output = None
        self._last_input = None
        self._last_time = None

    def update(self, feedback_value, in_time=None):
        """Calculates PID value for given reference feedback"""

        current_time = in_time if in_time is not None else self.current_time()
        if self._last_time is None:
            self._last_time = current_time

        # Fill PID information
        delta_time = current_time - self._last_time
        if not delta_time:
            delta_time = 1e-16
        elif delta_time < 0:
            return

        # Return last output if sample time not met
        if (
            self._sample_time is not None
            and self._last_output is not None
            and delta_time < self._sample_time
        ):
            return self._last_output

        # Calculate error
        error = self._set_point - feedback_value
        last_error = self._set_point - (
            self._last_input if self._last_input is not None else self._set_point
        )

        # Calculate delta error
        delta_error = error - last_error

        # Calculate P
        self._p_term = self._kp * error

        # Calculate I and avoids Sturation
        if self._last_output is None or (
            self._last_output > 0 and self._last_output < 100
        ):
            self._i_term += self._ki * error * delta_time
            self._i_term = self.clamp_value(self._i_term, self._windup)

        # Calculate D
        self._d_term = self._kd * delta_error / delta_time

        # Compute final output
        self._output = self._p_term + self._i_term + self._d_term
        self._output = self.clamp_value(self._output, (0, 100))

        # Keep Track
        self._last_output = self._output
        self._last_input = feedback_value
        self._last_time = current_time

    @property
    def kp(self):
        """Aggressively the PID reacts to the current error with setting Proportional Gain"""
        return self._kp

    @kp.setter
    def kp(self, value):
        self._kp = value

    @property
    def ki(self):
        """Aggressively the PID reacts to the current error with setting Integral Gain"""
        return self._ki

    @ki.setter
    def ki(self, value):
        self._ki = value

    @property
    def kd(self):
        """Determines how aggressively the PID reacts to the current
        error with setting Derivative Gain"""
        return self._kd

    @kd.setter
    def kd(self, value):
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
        self._windup = (-value, value)

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
    def p(self):
        return self._p_term

    @property
    def i(self):
        return self._i_term

    @property
    def d(self):
        return self._d_term

    @property
    def output(self):
        """PID result"""
        return self._output

    def log(self, message):
        if not self._logger:
            return
        self._logger.warning(message)

    def current_time(self):
        try:
            ret_time = time.monotonic()
        except AttributeError:
            ret_time = time.time()

        return ret_time

    def clamp_value(self, value, limits):
        lower, upper = limits

        if value is None:
            return None
        elif not lower and not upper:
            return value
        elif (upper is not None) and (value > upper):
            return upper
        elif (lower is not None) and (value < lower):
            return lower
        return value
