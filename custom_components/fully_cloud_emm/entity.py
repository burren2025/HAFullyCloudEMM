"""Shared entity helpers for Fully Cloud EMM."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import FullyCloudCoordinator, FullyCloudDevice


class FullyCloudEntity(CoordinatorEntity[FullyCloudCoordinator]):
    """Base Fully Cloud entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: FullyCloudCoordinator,
        device_id: str,
        field_key: str,
    ) -> None:
        super().__init__(coordinator)
        self._device_id = device_id
        self._field_key = field_key
        self._attr_unique_id = f"{DOMAIN}_{device_id}_{field_key}"

    @property
    def fully_device(self) -> FullyCloudDevice | None:
        """Return the current device payload for this entity."""
        return self.coordinator.data.get(self._device_id)

    @property
    def device_info(self) -> DeviceInfo:
        """Return Home Assistant device info."""
        device = self.fully_device
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            manufacturer="Fully Factory",
            name=device.name if device else self._device_id,
        )

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        return super().available and self.fully_device is not None

    @property
    def extra_state_attributes(self) -> dict[str, object] | None:
        """Return field metadata."""
        return {"field": self._field_key}


def field_name(field_key: str) -> str:
    """Convert a flattened payload key into an entity display name."""
    return field_key.replace("_", " ").title()

