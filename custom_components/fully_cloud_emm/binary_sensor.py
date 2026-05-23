"""Binary sensors for Fully Cloud EMM."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import FullyCloudCoordinator
from .entity import FullyCloudEntity, field_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry[FullyCloudCoordinator],
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Fully Cloud binary sensors."""
    coordinator = entry.runtime_data
    seen: set[tuple[str, str]] = set()

    def add_new_entities() -> None:
        entities: list[FullyCloudBinarySensor] = []
        for device_id, device in coordinator.data.items():
            for key, value in device.fields.items():
                if not isinstance(value, bool):
                    continue
                entity_key = (device_id, key)
                if entity_key in seen:
                    continue
                seen.add(entity_key)
                entities.append(FullyCloudBinarySensor(coordinator, device_id, key))

        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class FullyCloudBinarySensor(FullyCloudEntity, BinarySensorEntity):
    """A Fully Cloud boolean field."""

    def __init__(
        self, coordinator: FullyCloudCoordinator, device_id: str, field_key: str
    ) -> None:
        super().__init__(coordinator, device_id, field_key)
        self._attr_translation_key = "fully_cloud_field"
        self._attr_name = field_name(field_key)

    @property
    def is_on(self) -> bool | None:
        """Return the boolean field state."""
        device = self.fully_device
        if device is None:
            return None

        value: Any = device.fields.get(self._field_key)
        return bool(value) if isinstance(value, bool) else None

