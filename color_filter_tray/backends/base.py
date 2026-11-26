from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import IntEnum


class ColorFilterType(IntEnum):
    """
    Standard color filter types matching Windows 10/11 registry FilterType DWORD values,
    ordered in the UI according to the Windows 11 Accessibility > Color filters pane.
    """
    GRAYSCALE = 0
    INVERTED = 1
    GRAYSCALE_INVERTED = 2
    DEUTERANOPIA = 3
    PROTANOPIA = 4
    TRITANOPIA = 5


@dataclass(frozen=True)
class FilterOption:
    filter_type: ColorFilterType
    label: str
    short_label: str


# Ordered exactly as shown in the Windows 11 Color Filters screenshot (image_2.png)
UI_FILTER_OPTIONS: list[FilterOption] = [
    FilterOption(
        ColorFilterType.DEUTERANOPIA,
        "Red-green (green weak, deuteranopia)",
        "Deuteranopia (Green weak)",
    ),
    FilterOption(
        ColorFilterType.PROTANOPIA,
        "Red-green (red weak, protanopia)",
        "Protanopia (Red weak)",
    ),
    FilterOption(
        ColorFilterType.TRITANOPIA,
        "Blue-yellow (tritanopia)",
        "Tritanopia (Blue-yellow)",
    ),
    FilterOption(
        ColorFilterType.GRAYSCALE,
        "Grayscale",
        "Grayscale",
    ),
    FilterOption(
        ColorFilterType.GRAYSCALE_INVERTED,
        "Grayscale inverted",
        "Grayscale inverted",
    ),
    FilterOption(
        ColorFilterType.INVERTED,
        "Inverted",
        "Inverted",
    ),
]


@dataclass
class FilterState:
    active: bool
    filter_type: ColorFilterType


class ColorFilterBackend(ABC):
    """Abstract base class for OS-specific color filter controllers."""

    @abstractmethod
    def get_state(self) -> FilterState:
        """Read current active status and selected filter type from the OS."""
        raise NotImplementedError

    @abstractmethod
    def set_state(self, active: bool, filter_type: ColorFilterType) -> None:
        """Apply the active status and selected filter type immediately on the OS."""
        raise NotImplementedError

    def set_active(self, active: bool) -> FilterState:
        """Toggle color filters on/off while preserving the current filter type."""
        current = self.get_state()
        self.set_state(active, current.filter_type)
        return FilterState(active=active, filter_type=current.filter_type)

    def set_filter_type(self, filter_type: ColorFilterType) -> FilterState:
        """Switch the active filter type and apply immediately if active."""
        current = self.get_state()
        self.set_state(current.active, filter_type)
        return FilterState(active=current.active, filter_type=filter_type)

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Human-readable name of the active OS backend."""
        raise NotImplementedError
