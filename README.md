p # gnssraw

GNSS RINEX observation plotting and raw measurement analysis.

This project uses **uv** for dependency and environment management.

## Quick start

1. Install uv (Linux/macOS):

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Sync dependencies and create the local virtual environment:

```bash
uv sync
```

3. Run the plotting script (headless-friendly):

```bash
MPLBACKEND=Agg uv run app/plot_prcp.py 3019148c.23o --outdir outfigs
```

Output figures will be saved under the `outfigs/` directory.

## Common tasks

- Add a dependency:

```bash
uv add <package>
```

- Lock dependencies:

```bash
uv lock
```

- Update dependencies:

```bash
uv sync --upgrade
```

- Pin Python version for this project (optional):

```bash
uv python pin 3.11
```

## Notes

- The RINEX observation file referenced by the script should be present at `./3019148c.23o` or a path you provide via the CLI.
- The virtual environment is managed in `.venv/` by uv.

## RINEX Format Specifications

- [RINEX 3.05](https://files.igs.org/pub/data/format/rinex305.pdf) - Latest version
- [RINEX 3.04](https://files.igs.org/pub/data/format/rinex304.pdf) - Widely used version

## Reference Textbook

- [ESA GNSS Book, Volume I (TM-23)](https://gssc.esa.int/navipedia/GNSS_Book/ESA_GNSS-Book_TM-23_Vol_I.pdf) - Comprehensive GNSS fundamentals and measurement theory.

## Type Checking (mypy)

You can run static type checks with mypy.

- Install mypy as a dev dependency:

```bash
uv add --group dev mypy
```

- Run mypy against the `app` package:

```bash
uv run mypy app --pretty
```

Alternatively, if you have mypy installed in the local venv:

```bash
./.venv/bin/mypy app --pretty
```
