"""Tests for the --plot-goodstyle feature in plot_satellite_observations."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import matplotlib
import matplotlib.pyplot as plt
import pytest

matplotlib.use("Agg")

from app.gnss.plot.observables import _apply_goodstyle, plot_satellite_observations  # noqa: E402


def _make_minimal_epochs():
    """Return a minimal list of mock epoch objects sufficient for plotting."""
    signal_obs = MagicMock()
    signal_obs.pseudorange = 20_000_000.0
    signal_obs.carrier_phase = 100_000_000.0
    signal_obs.doppler_ = 1000.0
    signal_obs.snr = 40.0
    signal_obs.ambiguities = {}

    sat_obs = MagicMock()
    sat_obs.prn = 1
    sat_obs.signals = {"L1": signal_obs}
    sat_obs.ambiguities = {}

    from datetime import datetime

    epoch = MagicMock()
    epoch.datetime = datetime(2025, 1, 1, 0, 0, 0)
    epoch.satellites_gps = [sat_obs]
    epoch.satellites_qzss = []
    epoch.satellites_galileo = []
    epoch.satellites_glonass = []
    return [epoch]


def test_apply_goodstyle_hides_top_right_spines():
    """_apply_goodstyle should hide top and right spines on all axes."""
    fig, ax = plt.subplots()
    ax.plot([1, 2], [1, 2])
    _apply_goodstyle(fig, [ax])
    assert not ax.spines["top"].get_visible()
    assert not ax.spines["right"].get_visible()
    plt.close(fig)


def test_apply_goodstyle_sets_facecolors():
    """_apply_goodstyle should set white figure background and light axes background."""
    fig, ax = plt.subplots()
    _apply_goodstyle(fig, [ax])
    assert fig.get_facecolor() == matplotlib.colors.to_rgba("#ffffff")
    assert ax.get_facecolor() == matplotlib.colors.to_rgba("#fbfbfc")
    plt.close(fig)


def test_plot_satellite_observations_goodstyle_saves_file(tmp_path: Path):
    """plot_satellite_observations with goodstyle=True should produce output files."""
    epochs = _make_minimal_epochs()
    plot_satellite_observations(epochs, tmp_path, plot_mode=2, goodstyle=True)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) > 0, "Expected at least one PNG to be saved"


def test_plot_satellite_observations_no_goodstyle_saves_file(tmp_path: Path):
    """plot_satellite_observations with goodstyle=False (default) should still work."""
    epochs = _make_minimal_epochs()
    plot_satellite_observations(epochs, tmp_path, plot_mode=2, goodstyle=False)
    saved = list(tmp_path.glob("*.png"))
    assert len(saved) > 0, "Expected at least one PNG to be saved"
