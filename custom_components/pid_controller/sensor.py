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

from datetime import datetime
import logging
from math import floor, ceil
from typing import Any, Mapping, Optional
from statistics import mean

from decimal import Decimal


import voluptuous as vol
from _sha1 import sha1
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass
from homeassistant.const import (
    CONF_ENTITY_ID,
    CONF_NAME,
    CONF_ICON,
    CONF_UNIQUE_ID,
    EVENT_HOMEASSISTANT_START,
    STATE_UNAVAILABLE,
    CONF_MINIMUM,
    CONF_MAXIMUM,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_DEVICE_CLASS,
    STATE_ON,
    STATE_OFF,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import TemplateError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA
from homeassistant.helpers.event import async_track_state_change
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.template import result_as_boolean

# pylint: disable=wildcard-import, unused-wildcard-import
from .const import *
from .pidcontroller import PIDController as PID


_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = vol.All(
    PLATFORM_SCHEMA.extend(
        {
            vol.Optional(CONF_ENABLED, default=DEFAULT_ENABLED): cv.template,
            vol.Optional(CONF_ICON, default=DEFAULT_ICON): cv.template,
            vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
            vol.Optional(CONF_UNIQUE_ID): cv.string,
            vol.Required(CONF_SETPOINT): cv.template,
            vol.Optional(CONF_PROPORTIONAL, default=0): cv.template,
            vol.Optional(CONF_INTEGRAL, default=0): cv.template,
            vol.Optional(CONF_DERIVATIVE, default=0): cv.template,
            vol.Required(CONF_ENTITY_ID): cv.entity_id,
            vol.Optional(CONF_INVERT, default=False): cv.template,
            vol.Optional(CONF_PRECISION, default=DEFAULT_PRECISION): cv.template,
            vol.Optional(CONF_MINIMUM, default=DEFAULT_MINIMUM): cv.template,
            vol.Optional(CONF_MAXIMUM, default=DEFAULT_MAXIMUM): cv.template,
            vol.Optional(CONF_ROUND, default=DEFAULT_ROUND): cv.template,
            vol.Optional(CONF_SAMPLE_TIME, default=DEFAULT_SAMPLE_TIME): cv.template,
            vol.Optional(CONF_WINDUP, default=DEFAULT_WINDUP): cv.template,
            vol.Optional(CONF_WINDUP, default=DEFAULT_WINDUP): cv.template,
            vol.Optional(
                CONF_UNIT_OF_MEASUREMENT, default=DEFAULT_UNIT_OF_MEASUREMENT
            ): cv.template,
            vol.Optional(CONF_DEVICE_CLASS, default=DEFAULT_DEVICE_CLASS): cv.template,
        }
    )
)

# pylint: disable=unused-argument
async def async_setup_platform(
    hass: HomeAssistant, config, async_add_entities, discovery_info=None
):

    enabled = config.get(CONF_ENABLED)
    icon = config.get(CONF_ICON)
    set_point = config.get(CONF_SETPOINT)
    proportional = config.get(CONF_PROPORTIONAL)
    integral = config.get(CONF_INTEGRAL)
    derivative = config.get(CONF_DERIVATIVE)
    invert = config.get(CONF_INVERT)
    precision = config.get(CONF_PRECISION)
    minimum = config.get(CONF_MINIMUM)
    maximum = config.get(CONF_MAXIMUM)
    round_type = config.get(CONF_ROUND)
    sample_time = config.get(CONF_SAMPLE_TIME)
    windup = config.get(CONF_WINDUP)
    unit_of_measurement = config.get(CONF_UNIT_OF_MEASUREMENT)
    device_class = config.get(CONF_DEVICE_CLASS)

    ## Process Templates.
    for template in [
        enabled,
        icon,
        set_point,
        sample_time,
        windup,
        proportional,
        integral,
        derivative,
        invert,
        precision,
        minimum,
        maximum,
        round_type,
        unit_of_measurement,
        device_class,
    ]:
        if template is not None:
            template.hass = hass

    ## Set up platform.
    async_add_entities(
        [
            PidController(
                hass,
                config.get(CONF_UNIQUE_ID),
                config.get(CONF_NAME),
                enabled,
                icon,
                set_point,
                unit_of_measurement,
                device_class,
                sample_time,
                windup,
                proportional,
                integral,
                derivative,
                invert,
                minimum,
                maximum,
                round_type,
                precision,
                config.get(CONF_ENTITY_ID),
            )
        ]
    )


# pylint: disable=r0902
class PidController(SensorEntity):

    # pylint: disable=r0913
    def __init__(
        self,
        hass: HomeAssistant,
        unique_id,
        name,
        enabled,
        icon,
        set_point,
        unit_of_measurement,
        device_class,
        sample_time,
        windup,
        proportional,
        integral,
        derivative,
        invert,
        minimum,
        maximum,
        round_type,
        precision,
        entity_id,
    ):
        self._attr_name = name
        self._enabled_template = enabled
        self._icon_template = icon
        self._set_point_template = set_point
        self._unit_of_measurement_template = unit_of_measurement
        self._device_class_template = device_class
        self._sample_time_template = sample_time
        self._windup_template = windup
        self._attr_state = 0
        self._proportional_template = proportional
        self._integral_template = integral
        self._derivative_template = derivative
        self._invert_template = invert
        self._minimum_template = minimum
        self._maximum_template = maximum
        self._round_template = round_type
        self._precision_template = precision
        self._entities = []
        self._force_update = []
        self._reset_pid = []
        self._pid = None
        self._source = entity_id
        self._tunning = False
        self._tunning_data = {}

        self._enabled_entities = []
        self._p_entities = []
        self._i_entities = []
        self._d_entities = []

        self._get_entities()

        self._attr_unique_id = (
            str(
                sha1(
                    ";".join(
                        [
                            str(set_point),
                            str(proportional),
                            str(integral),
                            str(derivative),
                        ]
                    ).encode("utf-8")
                ).hexdigest()
            )
            if unique_id == "__legacy__"
            else unique_id
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return True

    @property
    def enabled(self) -> bool:
        """Enabled"""

        if self._enabled_template is not None:
            try:
                enabled = self._enabled_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ENABLED)
                return DEFAULT_ENABLED

            return bool(result_as_boolean(enabled))

        return DEFAULT_ENABLED

    @property
    def tunning(self) -> bool:
        """Returns Tunning"""
        return self._tunning

    @property
    def icon(self) -> str:
        """Returns Icon"""
        icon = DEFAULT_ICON
        if self._icon_template is not None:
            try:
                icon = self._icon_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ICON)
                icon = DEFAULT_ICON

        return icon

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""

        if not self.enabled:
            return 0

        state = 0
        try:
            state = float(self._attr_state) / 100
        except ValueError:
            state = 0

        if self.minimum > self.maximum:
            state = 0

        units = (self.maximum - self.minimum) * state
        state = self.minimum + units

        precision = pow(10, self.precision)

        if self.round == ROUND_FLOOR:
            state = floor(state * precision) / precision
        elif self.round == ROUND_CEIL:
            state = ceil(state * precision) / precision
        else:
            state = round(state, self.precision)

        if self.precision == 0:
            state = int(state)

        return state if self.available else STATE_UNAVAILABLE

    @property
    def raw_state(self) -> float:
        """Return the state of the sensor."""
        state = 0
        try:
            state = float(self._attr_state) / 100
        except ValueError:
            state = 0

        return float(state) if self.available else 0

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        """Return entity specific state attributes."""

        state_attr = {}

        for attr in ATTR_TO_PROPERTY:
            try:
                if getattr(self, attr) is not None:
                    state_attr[attr] = getattr(self, attr)
            except AttributeError:
                continue

        return state_attr

    @property
    def source(self) -> float:
        """Returns Response"""

        source_state = self.hass.states.get(self._source)
        if not source_state:
            return float(0)

        try:
            state = float(source_state.state)
        except ValueError:
            state = float(0)

        return float(state)

    @property
    def set_point(self) -> float:
        """Returns Set Point"""

        if self._set_point_template is not None:
            try:
                set_point = self._set_point_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_SETPOINT)
                return float(0)

            try:
                set_point = float(set_point)
            except (ValueError) as ex:
                set_point = 0

            return float(set_point)

        return float(0)

    @property
    def unit_of_measurement(self) -> str:
        """Returns Unit Of Measurement"""

        if self._unit_of_measurement_template is not None:
            try:
                unit_of_measurement = self._unit_of_measurement_template.async_render(
                    parse_result=False
                )
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_UNIT_OF_MEASUREMENT)
                unit_of_measurement = DEFAULT_UNIT_OF_MEASUREMENT

        return unit_of_measurement

    @property
    def device_class(self) -> SensorDeviceClass:
        """Returns Device Class"""

        if self._device_class_template is not None:
            try:
                device_class = self._device_class_template.async_render(
                    parse_result=False
                )
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_DEVICE_CLASS)
                device_class = DEFAULT_DEVICE_CLASS

        return device_class

    @property
    def sample_time(self) -> int:
        """Returns Sample Time"""

        if self._sample_time_template is not None:
            try:
                sample_time = self._sample_time_template.async_render(
                    parse_result=False
                )
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_SAMPLE_TIME)
                return int(DEFAULT_SAMPLE_TIME)

            try:
                sample_time = int(float(sample_time))
            except ValueError:
                sample_time = int(DEFAULT_SAMPLE_TIME)

            return int(sample_time)

        return int(DEFAULT_SAMPLE_TIME)

    @property
    def windup(self) -> int:
        """Returns Windup"""

        if self._windup_template is not None:
            try:
                windup = self._windup_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_WINDUP)
                return int(DEFAULT_WINDUP)

            try:
                windup = int(float(windup))
            except ValueError:
                windup = int(DEFAULT_WINDUP)

            return int(windup)

        return int(DEFAULT_WINDUP)

    @property
    def proportional(self) -> float:
        """Returns Proportional Band"""

        if self._proportional_template is not None:
            try:
                proportional = self._proportional_template.async_render(
                    parse_result=False
                )
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_PROPORTIONAL)
                return float(0)

            try:
                proportional = float(proportional)
            except (ValueError) as ex:
                proportional = 0

            if self.invert:
                proportional = proportional * -1

            return float(proportional)

        return float(0)

    @property
    def integral(self) -> float:
        """Returns Internal Band"""

        if self._integral_template is not None:
            try:
                integral = self._integral_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_INTEGRAL)
                return float(0)

            try:
                integral = float(integral)
            except ValueError:
                integral = 0

            if self.invert:
                integral = integral * -1

            return float(integral)

        return float(0)

    @property
    def derivative(self) -> float:
        """Returns Derivative Band"""

        if self._derivative_template is not None:
            try:
                derivative = self._derivative_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_DERIVATIVE)
                return float(0)

            try:
                derivative = float(derivative)
            except ValueError:
                derivative = 0

            if self.invert:
                derivative = derivative * -1

            return float(derivative)

        return float(0)

    @property
    def minimum(self) -> float:
        """Returns Minimum"""

        if self._minimum_template is not None:
            try:
                minimum = self._minimum_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_MINIMUM)
                return float(DEFAULT_MINIMUM)

            try:
                minimum = float(minimum)
            except ValueError:
                minimum = float(DEFAULT_MINIMUM)

            return minimum

        return DEFAULT_MINIMUM

    @property
    def maximum(self) -> float:
        """Returns Maximum"""

        if self._maximum_template is not None:
            try:
                maximum = self._maximum_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_MAXIMUM)
                return float(DEFAULT_MAXIMUM)

            try:
                maximum = float(maximum)
            except ValueError:
                maximum = float(DEFAULT_MAXIMUM)

            return maximum

        return DEFAULT_MAXIMUM

    @property
    def round(self) -> str:
        """Returns Round Type"""

        if self._round_template is not None:
            try:
                round_type = self._round_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ROUND)
                return False

            return str(round_type).lower()

        return DEFAULT_ROUND

    @property
    def invert(self) -> bool:
        """Returns Inverted State"""

        if self._invert_template is not None:
            try:
                invert = self._invert_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_INVERT)
                return False

            return bool(result_as_boolean(invert))

        return False

    @property
    # pylint: disable=invalid-name
    def p(self) -> float:
        """Calculated Proportional Gain"""
        if not self._pid:
            return float(0)

        p = self._pid.p

        return float(p)

    @property
    # pylint: disable=invalid-name
    def i(self) -> float:
        """Calculated Integral Gain"""
        if not self._pid:
            return float(0)

        i = self._pid.i

        return float(i)

    @property
    # pylint: disable=invalid-name
    def d(self) -> float:
        """Calculated Derivative Gain"""
        if not self._pid:
            return float(0)

        d = self._pid.d

        return float(d)

    @property
    def precision(self) -> int:
        """Returns Precision"""

        if self._precision_template is not None:
            try:
                precision = self._precision_template.async_render(parse_result=False)
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_PRECISION)
                return int(DEFAULT_PRECISION)

            try:
                precision = int(float(precision))
            except ValueError:
                precision = int(DEFAULT_PRECISION)

            return int(precision)

        return int(DEFAULT_PRECISION)

    @staticmethod
    def show_template_exception(ex, field) -> None:
        """Show Template Erros"""
        if ex.args and ex.args[0].startswith("UndefinedError: 'None' has no attribute"):
            # Common during HA startup - so just a warning
            _LOGGER.warning(ex)

        else:
            _LOGGER.error('Error parsing template for field "%s": %s', field, ex)

    def _get_entities(self) -> None:
        self._entities = []
        self._force_update = []

        if self._icon_template is not None:
            try:
                info = self._icon_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ICON)
            else:
                self._entities += info.entities

        if self._set_point_template is not None:
            try:
                info = self._set_point_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_SETPOINT)
            else:
                self._entities += info.entities
                self._reset_pid += info.entities

        if self._unit_of_measurement_template is not None:
            try:
                info = self._unit_of_measurement_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_UNIT_OF_MEASUREMENT)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._device_class_template is not None:
            try:
                info = self._device_class_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_DEVICE_CLASS)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._sample_time_template is not None:
            try:
                info = self._sample_time_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_SAMPLE_TIME)
            else:
                self._entities += info.entities

        if self._windup_template is not None:
            try:
                info = self._windup_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_WINDUP)
            else:
                self._entities += info.entities

        if self._enabled_template is not None:
            try:
                info = self._enabled_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ENABLED)
            else:
                self._entities += info.entities
                self._enabled_entities += info.entities

        if self._proportional_template is not None:
            try:
                info = self._proportional_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_PROPORTIONAL)
            else:
                self._entities += info.entities
                self._p_entities += info.entities

        if self._integral_template is not None:
            try:
                info = self._integral_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_INTEGRAL)
            else:
                self._entities += info.entities
                self._i_entities += info.entities

        if self._derivative_template is not None:
            try:
                info = self._derivative_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_DERIVATIVE)
            else:
                self._entities += info.entities
                self._d_entities += info.entities

        if self._precision_template is not None:
            try:
                info = self._precision_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_PRECISION)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._minimum_template is not None:
            try:
                info = self._minimum_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_MINIMUM)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._maximum_template is not None:
            try:
                info = self._maximum_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_MAXIMUM)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._round_template is not None:
            try:
                info = self._round_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_ROUND)
            else:
                self._entities += info.entities
                self._force_update += info.entities

        if self._invert_template is not None:
            try:
                info = self._invert_template.async_render_to_info()
            except (TemplateError, TypeError) as ex:
                self.show_template_exception(ex, CONF_INVERT)
            else:
                self._entities += info.entities
                self._force_update += info.entities
                self._reset_pid += info.entities

        self._entities += [self._source]

    def reset_pid(self):
        if self._pid:
            self._pid.reset_pid()

    def update(self) -> None:
        """Update the sensor state if it needed."""
        self._update_sensor()

    def _update_sensor(self, entity=None) -> None:
        if self.set_point == 0:
            self._attr_state = 0
            return

        if entity in self._reset_pid:
            self.reset_pid()

        source = self.source
        set_point = self.set_point

        if self.proportional == 0 and self.integral == 0 and self.derivative == 0:
            self._attr_state = 0 if self.invert else 100
            if source >= set_point:
                self._attr_state = 100 if self.invert else 0
            if self._tunning:
                self.feedback_autotune()
        else:
            if self._pid is None:
                self._pid = PID(self.proportional, self.integral, self.derivative)
            else:
                if self.proportional != self._pid.kpg:
                    self._pid.kpg = self.proportional
                if self.integral != self._pid.kig:
                    self._pid.kig = self.integral
                if self.derivative != self._pid.kdg:
                    self._pid.kdg = self.derivative

            if self.sample_time != self._pid.sample_time:
                self._pid.sample_time = self.sample_time

            if self.windup != self._pid.windup:
                self._pid.windup = self.windup

            if set_point != self._pid.set_point:
                self.reset_pid()
                self._pid.set_point = set_point

            self._pid.update(source)
            if self._tunning:
                self.feedback_autotune()

            output = float(self._pid.output)

            output = max(min(output, 100), 0)
            self._attr_state = output

    async def async_added_to_hass(self) -> None:
        """Register callbacks."""

        # pylint: disable=unused-argument
        @callback
        def sensor_state_listener(entity, old_state, new_state):
            """Handle device state changes."""
            last_state = self.state
            self._update_sensor(entity=entity)
            if last_state != self.state or entity in self._force_update:
                self.async_schedule_update_ha_state(True)

        # pylint: disable=unused-argument
        @callback
        def sensor_startup(event):
            """Update template on startup."""

            self._update_sensor()

            self.async_schedule_update_ha_state(True)

            ## process listners
            for entity in self._entities:
                async_track_state_change(self.hass, entity, sensor_state_listener)

        self.hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, sensor_startup)

    def start_autotune(self):
        if self.set_point == 0:
            return

        if len(self._enabled_entities) != 1:
            return

        ## Returns Entity in p/i/d
        if len(self._p_entities) != 1:
            return

        if len(self._i_entities) != 1:
            return

        if len(self._d_entities) != 1:
            return

        if self.source > self.set_point:
            return

        self._tunning_data = {}

        old_data = {"p": self.p, "i": self.i, "d": self.d, "set": self.source}
        self._tunning_data["old_data"] = old_data

        self.update_entity(self._enabled_entities[0], STATE_OFF)
        self.update_entity(self._p_entities[0], 0)
        self.update_entity(self._i_entities[0], 0)
        self.update_entity(self._d_entities[0], 0)
        self.reset_pid()

        self._tunning_data["tunning_stage"] = "warming"
        self._tunning_data["start_time"] = datetime.now()
        self._tunning_data["start_feedback"] = self.source
        self._tunning_data["stage_time"] = self._tunning_data["start_time"].timestamp()
        self._tunning_data["cross_time"] = []
        self._tunning_data["overshoot"] = []

        self.hass.states.async_set(self._enabled_entities[0], STATE_ON)

        self._tunning = True

    def feedback_autotune(self):
        ### http://faculty.mercer.edu/jenkins_he/documents/TuningforPIDControllers.pdf

        if not self._tunning:
            return

        call_time = datetime.now().timestamp()
        stage_time = self._tunning_data["stage_time"]
        delta_stage = abs(call_time - stage_time)
        delta_point = abs(self.source - self.set_point)

        if self._tunning_data["tunning_stage"] == "warming":
            if self.source >= self.set_point:
                self._tunning_data["cross_time"].append(delta_stage)
                self._tunning_data["overshoot"].append(delta_point)
                self._tunning_data["tunning_stage"] = "cooling"

        elif self._tunning_data["tunning_stage"] == "cooling":
            delta_mean = mean(self._tunning_data["overshoot"])
            target_cooling = self.set_point - delta_mean
            if self.source <= target_cooling:
                self._tunning_data["cross_time"].append(delta_stage)
                self._tunning_data["overshoot"].append(delta_point)
                self._tunning_data["tunning_stage"] = "warming"
            if len(self._tunning_data["overshoot"]) >= 4:
                self._tunning_data["tunning_stage"] = "result"

        elif self._tunning_data["tunning_stage"] == "result":
            self.hass.states.async_set(self._enabled_entities[0], STATE_OFF)
            start_feedback = self._tunning_data["start_feedback"]
            mean_overshoot = mean(self._tunning_data["overshoot"])
            overshoot_time = self.get_time(
                0,
                start_feedback,
                mean(self._tunning_data["cross_time"]),
                mean_overshoot,
                self.set_point,
            )

            # First Method Calculation
            p_value = 2 * mean_overshoot
            i_value = overshoot_time * 2
            d_value = overshoot_time / 2

            pcr_calculation = []

            for inx, val in enumerate(self._tunning_data["cross_time"]):
                if inx == 0:
                    continue
                if (inx % 2) == 0:
                    pcr_value = abs(val - self._tunning_data["cross_time"][inx - 2])
                    pcr_calculation.append(pcr_value)

            pcr_value = mean(pcr_calculation)

            p_value2 = 0.6 * p_value
            i_value2 = 0.5 * pcr_value
            d_value2 = 0.125 * pcr_value

            self._tunning_data["result"] = {"p": p_value2, "i": i_value2, "d": d_value2}
            self.stop_autotune()

        self._tunning_data["stage_time"] = call_time

    def stop_autotune(self):
        self.update_entity(self._enabled_entities[0], STATE_ON)
        self.reset_pid()

        if self._tunning_data["result"]:
            self.update_entity(self._p_entities[0], self._tunning_data["result"]["p"])
            self.update_entity(self._i_entities[0], self._tunning_data["result"]["i"])
            self.update_entity(self._d_entities[0], self._tunning_data["result"]["d"])

        self._tunning = False
        self._tunning_data = {}

    def update_entity(self, entity_id, state):
        entity = self.hass.states.get(entity_id)
        if not entity:
            return
        self.hass.states.async_set(entity_id, state, entity.attributes)

    def get_time(self, stat_time, start_temp, end_time, end_temperature, target):
        m, c = self.line_equation(stat_time, start_temp, end_time, end_temperature)
        return (target - c) / m

    def line_equation(self, x1, y1, x2, y2):
        """y = {m}x + {c}"""
        m = (y2 - y1) / (x2 - x1)
        c = y2 - (m * x2)
        return m, c
