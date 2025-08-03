"""MPK Łódź"""
import logging

from .consts import DOMAIN

_LOGGER = logging.getLogger(__name__)

# async def async_setup(hass, config):
#     return True


# async def async_setup_entry(hass, config_entry):
#     hass.async_create_task(hass.config_entries.async_forward_entry_setups(config_entry, ["sensor"]))
#     return True


# async def async_unload_entry(hass, config_entry):
#     await hass.config_entries.async_forward_entry_unload(config_entry, "sensor")
#     hass.data[DOMAIN].pop(config_entry.entry_id)
#     return True
