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
import logging
from distutils import util

import homeassistant.helpers.config_validation as cv
from homeassistant.core import HomeAssistant
from homeassistant.helpers.service import verify_domain_control
from homeassistant.const import ATTR_ENTITY_ID
from homeassistant.exceptions import HomeAssistantError

import voluptuous as vol

# pylint: disable=wildcard-import, unused-wildcard-import
from .const import *

__version__ = VERSION

_LOGGER = logging.getLogger(__name__)

SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_ENTITY_ID): cv.entity_id,
    }
)

# pylint: disable=unused-argument
async def async_setup(hass: HomeAssistant, config):
    """Set up a pid."""

    _LOGGER.debug("setup")

    async def async_pid_service_reset(call) -> None:
        """Call pid service handler."""
        _LOGGER.info("%s service called", call.service)
        await pid_reset_service(hass, call)

    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_RESET_PID,
        async_pid_service_reset,
        schema=SERVICE_SCHEMA,
    )

    async def async_pid_service_autotune(call) -> None:
        """Call pid service handler."""
        _LOGGER.info("%s service called", call.service)
        await pid_autotune_service(hass, call)

    hass.services.async_register(
        COMPONENT_DOMAIN,
        SERVICE_AUTOTUNE,
        async_pid_service_autotune,
        schema=SERVICE_SCHEMA,
    )

    return True


def get_entity_from_domain(hass: HomeAssistant, domain, entity_id):
    component = hass.data.get(domain)
    if component is None:
        raise HomeAssistantError(f"{domain} component not set up")

    entity = component.get_entity(entity_id)
    if entity is None:
        raise HomeAssistantError(f"{entity_id} not found")

    return entity


async def pid_reset_service(hass: HomeAssistant, call):
    entity_id = call.data["entity_id"]
    domain = entity_id.split(".")[0]

    _LOGGER.info("%s reset pid", entity_id)

    try:
        get_entity_from_domain(hass, domain, entity_id).reset_pid()
    except AttributeError:
        raise HomeAssistantError(f"{entity_id} can't reset PID") from AttributeError


async def pid_autotune_service(hass: HomeAssistant, call):
    entity_id = call.data["entity_id"]
    domain = entity_id.split(".")[0]

    _LOGGER.info("%s autotune pid", entity_id)

    try:
        get_entity_from_domain(hass, domain, entity_id).start_autotune()
    except AttributeError:
        raise HomeAssistantError(f"{entity_id} can't reset PID") from AttributeError
