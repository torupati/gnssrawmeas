"""Deprecated: moved to misc/gnss_ambiguity.py."""

from misc.gnss_ambiguity import (
    get_widelane_ambiguity,
    get_narrowlane_ambiguity,
    get_ionospheric_ambiguity,
    calculate_double_difference_widelane_ambiguity,
    calculate_double_difference_ionospheric_ambiguity,
    calculate_double_difference,
)

__all__ = [
    "get_widelane_ambiguity",
    "get_narrowlane_ambiguity",
    "get_ionospheric_ambiguity",
    "calculate_double_difference_widelane_ambiguity",
    "calculate_double_difference_ionospheric_ambiguity",
    "calculate_double_difference",
]
