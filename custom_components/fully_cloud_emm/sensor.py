"""Sensors for Fully Cloud EMM."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FullyCloudCoordinator
from .entity import FullyCloudEntity, field_name

MAX_STATE_LENGTH = 255


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[FullyCloudCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fully Cloud sensors."""
    coordinator = entry.runtime_data
    seen: set[tuple[str, str]] = set()

    def add_new_entities() -> None:
        entities: list[FullyCloudSensor] = []
        for device_id, device in coordinator.data.items():
            for key, value in device.fields.items():
                if isinstance(value, bool) or value is None or isinstance(value, Mapping):
                    continue
                entity_key = (device_id, key)
                if entity_key in seen:
                    continue
                seen.add(entity_key)
                entities.append(FullyCloudSensor(coordinator, device_id, key))

        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class FullyCloudSensor(FullyCloudEntity, SensorEntity):
    """A Fully Cloud scalar field."""

    def __init__(
        self, coordinator: FullyCloudCoordinator, device_id: str, field_key: str
    ) -> None:
        super().__init__(coordinator, device_id, field_key)
        self._attr_name = field_name(field_key)
        self._apply_field_metadata(field_key)

    @property
    def native_value(self) -> str | int | float | None:
        """Return the field value."""
        device = self.fully_device
        if device is None:
            return None

        value: Any = device.fields.get(self._field_key)
        if isinstance(value, (int, float, str)):
            if isinstance(value, str) and len(value) > MAX_STATE_LENGTH:
                return value[:MAX_STATE_LENGTH]
            return value

        if isinstance(value, list):
            return len(value)

        if value is None:
            return None

        return str(value)[:MAX_STATE_LENGTH]

    def _apply_field_metadata(self, field_key: str) -> None:
        key = field_key.lower()

        if "battery" in key and ("level" in key or key.endswith("battery")):
            self._attr_device_class = SensorDeviceClass.BATTERY
            self._attr_native_unit_of_measurement = PERCENTAGE
            self._attr_state_class = SensorStateClass.MEASUREMENT
            return

        if key.endswith("temperature") or "_temperature_" in key:
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
            self._attr_state_class = SensorStateClass.MEASUREMENT
            return

        if "voltage" in key:
            self._attr_device_class = SensorDeviceClass.VOLTAGE
            self._attr_native_unit_of_measurement = UnitOfElectricPotential.VOLT
            self._attr_state_class = SensorStateClass.MEASUREMENT
            return

        if isinstance(self.native_value, (int, float)):
            self._attr_state_class = SensorStateClass.MEASUREMENT

