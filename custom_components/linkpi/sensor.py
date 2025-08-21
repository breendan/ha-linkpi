import logging
from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SENSOR_TYPES = {
    "system_cpu": ["CPU Usage", "%"],
    "system_mem": ["Memory Usage", "%"],
    "system_temp": ["Core Temperature", "°C"],
    "net_tx_rate": ["Network TX Rate", "kbps"],
    "net_rx_rate": ["Network RX Rate", "kbps"],
}

def parse_states(states):
    """
    Parse raw coordinator data into a flat dict of sensor values.
    Negative network rates are considered invalid and are clamped to 0.
    """
    if not isinstance(states, dict):
        return {key: None for key in SENSOR_TYPES}

    sys_data = states.get("system", {})
    net_data = states.get("network", {})

    tx = net_data.get("tx")
    rx = net_data.get("rx")

    # Simple clamping logic to prevent erronous values being recorded
    corrected_tx = False
    corrected_rx = False

    if isinstance(tx, (int, float)) and tx < 0:
        _LOGGER.debug("Clamping negative net_tx_rate value %s to 0", tx)
        tx = 0
        corrected_tx = True

    if isinstance(rx, (int, float)) and rx < 0:
        _LOGGER.debug("Clamping negative net_rx_rate value %s to 0", rx)
        rx = 0
        corrected_rx = True

    parsed = {
        "system_cpu": sys_data.get("cpu"),
        "system_mem": sys_data.get("mem"),
        "system_temp": sys_data.get("temperature"),
        "net_tx_rate": tx,
        "net_rx_rate": rx,
    }

    return parsed

async def async_setup_entry(hass, config_entry, async_add_entities):
    coordinator = hass.data[DOMAIN][config_entry.entry_id]["coordinator"]
    sensors = []

    # Add static system/network sensors
    for key, (name, unit) in SENSOR_TYPES.items():
        sensors.append(LinkPiSensor(coordinator, key, name, unit))

    # Add dynamic video input sensors
    vi_data = coordinator.data.get("video_input", [])
    for vi_input in vi_data:
        sensors.append(LinkPiVideoInputSensor(coordinator, vi_input))

    async_add_entities(sensors)

class LinkPiSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, key, name, unit):
        super().__init__(coordinator)
        self._attr_name = f"LinkPi Encoder {name}"
        self._attr_unique_id = f"{coordinator.name}_{key}"
        self._key = key
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        state = parse_states(self.coordinator.data)
        return state.get(self._key)

    @property
    def available(self):
        return self.coordinator.data is not None

class LinkPiVideoInputSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, vi_input):
        super().__init__(coordinator)
        self._chnId = vi_input["chnId"]
        self._input_name = vi_input["name"]
        self._attr_name = f"LinkPi {self._input_name} (chn{self._chnId})"
        self._attr_unique_id = f"{coordinator.name}_video_{self._chnId}"

    @property
    def native_value(self):
        # Search for the matching input in the latest data
        for vi_input in self.coordinator.data.get("video_input", []):
            if vi_input["chnId"] == self._chnId:
                return "on" if vi_input.get("avalible") else "off" # Spelling is incorrect in LinkPi
        return None

    @property
    def available(self):
        # Sensor is always available if input is reported
        for vi_input in self.coordinator.data.get("video_input", []):
            if vi_input["chnId"] == self._chnId:
                return True
        return False

    @property
    def extra_state_attributes(self):
        for vi_input in self.coordinator.data.get("video_input", []):
            if vi_input["chnId"] == self._chnId:
                # Return all fields except chnId and name
                return {k: v for k, v in vi_input.items() if k not in ["chnId", "name"]}
        return {}

    @property
    def icon(self):
        # Use HDMI icon for HDMI, fallback otherwise
        for vi_input in self.coordinator.data.get("video_input", []):
            if vi_input["chnId"] == self._chnId:
                if vi_input.get("protocol") == "HDMI":
                    return "mdi:video-input-hdmi"
        return "mdi:video-input-component"
