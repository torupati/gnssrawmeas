from pathlib import Path

import pytest

from app import rnxproc


@pytest.fixture
def sample_rinex_file():
    """Return the path to a sample RINEX file."""
    sample_file = (
        Path(__file__).parent.parent
        / "sample_data"
        / "static_baseline"
        / "3075358x.25o"
    )
    if not sample_file.exists():
        pytest.skip(f"Sample RINEX file not found: {sample_file}")
    return sample_file


def test_main_missing_signal_code_map_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_rinex_file: Path
):
    missing_map = tmp_path / "missing_signal_code_map.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "rnxproc",
            str(sample_rinex_file),
            "--outdir",
            str(tmp_path / "out"),
            "--signal-code-map",
            str(missing_map),
        ],
    )

    assert rnxproc.main() == 1


def test_main_invalid_signal_code_map_returns_1(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, sample_rinex_file: Path
):
    invalid_map = tmp_path / "invalid_signal_code_map.json"
    invalid_map.write_text("{", encoding="utf-8")

    monkeypatch.setattr(
        "sys.argv",
        [
            "rnxproc",
            str(sample_rinex_file),
            "--outdir",
            str(tmp_path / "out"),
            "--signal-code-map",
            str(invalid_map),
        ],
    )

    assert rnxproc.main() == 1
