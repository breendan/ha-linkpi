import logging
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, CONF_HOST, CONF_USERNAME, CONF_PASSWORD, CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
from .encoderapi import LinkPiEncoder

_LOGGER = logging.getLogger(__name__)

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

async def _test_connection(host: str, username: str, password: str) -> None:
    """Try logging into the LinkPi device to confirm credentials."""
    encoder = LinkPiEncoder(host, username, password)
    try:
        await encoder.login()
    except Exception:
        raise CannotConnect
    finally:
        await encoder.close()

class LinkpiConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for LinkPi Encoder."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _test_connection(
                    user_input[CONF_HOST],
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                )
                return self.async_create_entry(
                    title=user_input[CONF_HOST],
                    data=user_input,
                )
            except CannotConnect:
                _LOGGER.error("Unable to connect to LinkPi at %s", user_input[CONF_HOST])
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error during LinkPi config flow")
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_HOST): str,
            vol.Required(CONF_USERNAME): str,
            vol.Required(CONF_PASSWORD): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return LinkPiOptionsFlowHandler(config_entry)


class LinkPiOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow for LinkPi Encoder."""

    def __init__(self, config_entry):
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Manage the LinkPi options."""
        errors: dict[str, str] = {}
        current_scan = self._config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)

        if user_input is not None:
            try:
                host = self._config_entry.data[CONF_HOST]
                username = self._config_entry.data[CONF_USERNAME]
                password = self._config_entry.data[CONF_PASSWORD]

                await _test_connection(host, username, password)

                return self.async_create_entry(
                    title="",
                    data={CONF_SCAN_INTERVAL: user_input[CONF_SCAN_INTERVAL]},
                )
            except CannotConnect:
                _LOGGER.error("Unable to connect to LinkPi at %s", host)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Error saving LinkPi options")
                errors["base"] = "unknown"

        schema = vol.Schema({
            vol.Required(CONF_SCAN_INTERVAL, default=current_scan): vol.All(
                int, vol.Range(min=10, max=3600)
            )
        })

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            errors=errors,
        )
