"""Smoke tests for the --plot-goodstyle / goodstyle=True feature."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib.pyplot as plt
import pytest

from app.gnss.plot.observables import (
    _GOODSTYLE_RC,
    _apply_goodstyle_axes,
    _goodstyle_context,
    plot_satellite_observations,
)


def _make_minimal_epochs():
    """Return a minimal list of mock EpochObservations for testing."""
    signal_obs = MagicMock()
    signal_obs.pseudorange = 20_000_000.0
    signal_obs.carrier_phase = 100_000.0
    signal_obs.doppler_ = -1000.0
    signal_obs.snr = 45.0

    sat_obs = MagicMock()
    sat_obs.prn = 1
    sat_obs.signals = {"L1": signal_obs}
    sat_obs.ambiguities = {}

    epoch = MagicMock()
    epoch.datetime = datetime(2025, 1, 1, 0, 0, 0)
    epoch.satellites_gps = [sat_obs]
    epoch.satellites_qzss = []
    epoch.satellites_galileo = []
    epoch.satellites_glonass = []

    return [epoch]


def test_goodstyle_context_applies_rcparams():
    """rc_context should temporarily set the goodstyle rcParams."""
    original_facecolor = plt.rcParams["figure.facecolor"]
    with _goodstyle_context(True):
        assert plt.rcParams["figure.facecolor"] == _GOODSTYLE_RC["figure.facecolor"]
    # After the context, rcParams should be restored
    assert plt.rcParams["figure.facecolor"] == original_facecolor


def test_goodstyle_context_disabled_leaves_rcparams_unchanged():
    """When disabled, _goodstyle_context must not change any rcParams."""
    original_facecolor = plt.rcParams["figure.facecolor"]
    with _goodstyle_context(False):
        assert plt.rcParams["figure.facecolor"] == original_facecolor


def test_apply_goodstyle_axes_hides_top_right_spines():
    """_apply_goodstyle_axes should hide top and right spines."""
    fig, ax = plt.subplots()
    _apply_goodstyle_axes(ax)
    assert not ax.spines["top"].get_visible()
    assert not ax.spines["right"].get_visible()
    plt.close(fig)


def test_plot_satellite_observations_goodstyle_saves_file(tmp_path: Path):
    """plot_satellite_observations with goodstyle=True should still save a file."""
    epochs = _make_minimal_epochs()
    plot_satellite_observations(epochs, tmp_path, plot_mode=2, goodstyle=True)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) == 1


def test_plot_satellite_observations_default_saves_file(tmp_path: Path):
    """plot_satellite_observations with goodstyle=False (default) should save a file."""
    epochs = _make_minimal_epochs()
    plot_satellite_observations(epochs, tmp_path, plot_mode=2, goodstyle=False)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) == 1
