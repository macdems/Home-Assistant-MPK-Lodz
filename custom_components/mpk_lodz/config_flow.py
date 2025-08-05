from types import MappingProxyType

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import device_registry, entity_registry

from .const import CONF_DIRECTIONS, CONF_LINES, CONF_STOPID, CONF_STOPNUM, DOMAIN
from .sensor import MpkLodzSensor


class CoerceOrNone(vol.Coerce):
    """Coerce to a type or None if the value is None."""

    def __call__(self, value):
        if value is None:
            return None
        return super().__call__(value)


class ValidatedSchema(vol.Schema):
    """Validator that ensures exactly one of the specified keys is present."""

    def __init__(self, schema):
        super().__init__(schema)

    def __call__(self, value):
        if (value.get(CONF_STOPNUM) is None) == (value.get(CONF_STOPID) is None):
            raise vol.MultipleInvalid([
                vol.Invalid("both_or_neither", path=[CONF_STOPNUM]),
                vol.Invalid("both_or_neither", path=[CONF_STOPID])
            ])
        return super().__call__(value)


PARENT_SCHEMA = vol.Schema({vol.Required(CONF_NAME, default="MPK Łódź"): str})


def stop_config_schema(values={}):
    return ValidatedSchema({
        vol.Optional(CONF_STOPID, default=None, description={"suggested_value": values.get(CONF_STOPID, "")}): CoerceOrNone(int),
        vol.Optional(CONF_STOPNUM, default=None, description={"suggested_value": values.get(CONF_STOPNUM, "")}): CoerceOrNone(int),
        vol.Optional(CONF_NAME, default="", description={"suggested_value": values.get(CONF_NAME, "")}): str,
        vol.Optional(CONF_LINES, default="", description={"suggested_value": values.get(CONF_LINES, "")}): str,
        vol.Optional(CONF_DIRECTIONS, default="", description={"suggested_value": values.get(CONF_DIRECTIONS, "")}): str,
    })


class MpkLodzConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        # Prevent duplicates (only one instance allowed)
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(step_id="user", data_schema=PARENT_SCHEMA)

    @classmethod
    @callback
    def async_get_supported_subentry_types(cls, config_entry):
        return {"stop": MpkLodzSubentryFlowHandler}


class MpkLodzSubentryFlowHandler(config_entries.ConfigSubentryFlow):

    @staticmethod
    def _make_uid(data):
        stop_id = data.get(CONF_STOPID)
        stop_num = data.get(CONF_STOPNUM)
        lines = [line.strip() for line in data.get(CONF_LINES, "").split(',')]
        directions = [dir.strip() for dir in data.get(CONF_DIRECTIONS, "").split(',')]
        return f"{stop_id or f'num{stop_num}'}_{','.join(lines)}_{','.join(directions)}"

    async def _get_stop_title(self, user_input):
        if stop_name := user_input.get(CONF_NAME):
            result = stop_name
        else:
            if user_input.get(CONF_STOPID):
                stop = user_input.get(CONF_STOPID)
                use_stop_num = False
            else:
                stop = user_input.get(CONF_STOPNUM)
                use_stop_num = True
            real_stop_name = await MpkLodzSensor.get_stop_name(self.hass, stop, use_stop_num)
            if real_stop_name:
                user_input[CONF_NAME] = real_stop_name
                result = real_stop_name
            else:
                result = f"#{user_input.get(CONF_STOPID) or user_input.get(CONF_STOPNUM)}"
        if user_input.get(CONF_LINES):
            result += f": {', '.join(user_input.get(CONF_LINES).split(','))}"
        if user_input.get(CONF_DIRECTIONS):
            result += f" → {', '.join(user_input.get(CONF_DIRECTIONS).split(','))}"
        return result

    async def async_step_user(self, user_input=None):
        if user_input is not None:
            title = await self._get_stop_title(user_input)
            # return self.async_create_entry(title=title, data=user_input)  # it does not update entities
            config_entry = self._get_entry()
            if self.hass.config_entries.async_add_subentry(
                config_entry,
                config_entries.ConfigSubentry(
                    data=MappingProxyType(user_input),
                    subentry_type='stop',
                    title=title,
                    unique_id=self._make_uid(user_input),
                ),
            ):
                self.hass.config_entries.async_schedule_reload(config_entry.entry_id)
            return self.async_abort(reason="create_entry", description_placeholders={"name": title})

        return self.async_show_form(
            step_id="user",
            data_schema=stop_config_schema(),
        )

    async def async_step_reconfigure(self, user_input):
        config_subentry = self._get_reconfigure_subentry()

        if user_input is not None:
            data = config_subentry.data | user_input
            title = await self._get_stop_title(data)
            config_entry = self._get_entry()
            new_uid = self._make_uid(data)
            if new_uid != config_subentry.unique_id:
                dr = device_registry.async_get(self.hass)
                er = entity_registry.async_get(self.hass)
                dr.async_clear_config_subentry(config_entry.entry_id, config_subentry.subentry_id)
                er.async_clear_config_subentry(config_entry.entry_id, config_subentry.subentry_id)
            if self.hass.config_entries.async_update_subentry(
                entry=config_entry,
                subentry=config_subentry,
                title=title,
                data=data,
                unique_id=new_uid,
            ):
                self.hass.config_entries.async_schedule_reload(config_entry.entry_id)
            return self.async_abort(reason="reconfigure_successful", description_placeholders={"name": title})

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=stop_config_schema(config_subentry.data),
        )
