import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    DOMAIN,
    CONF_API_KEY,
    CONF_API_SECRET,
    CONF_POLL_INTERVAL,
    CONF_DEBUG,
)


class BitvavoEnhancedConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            if not user_input[CONF_API_KEY].strip():
                errors["api_key"] = "invalid_api_key"

            if not user_input[CONF_API_SECRET].strip():
                errors["api_secret"] = "invalid_api_secret"

            if not errors:
                # Default options
                return self.async_create_entry(
                    title="Bitvavo Enhanced",
                    data=user_input,
                    options={
                        CONF_POLL_INTERVAL: 60,
                        CONF_DEBUG: False,
                    }
                )

        schema = vol.Schema({
            vol.Required(CONF_API_KEY): str,
            vol.Required(CONF_API_SECRET): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return BitvavoEnhancedOptionsFlow(config_entry)


class BitvavoEnhancedOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        schema = vol.Schema({
            vol.Required(
                CONF_POLL_INTERVAL,
                default=self.config_entry.options.get(CONF_POLL_INTERVAL, 60)
            ): vol.All(int, vol.Range(min=10, max=600)),

            vol.Required(
                CONF_DEBUG,
                default=self.config_entry.options.get(CONF_DEBUG, False)
            ): bool,
        })

        return self.async_show_form(step_id="init", data_schema=schema)
