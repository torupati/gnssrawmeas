# gnssraw

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

## REST API Usage

You can also run the functionality as a REST API using FastAPI:

### Start the API Server

```bash
uv run uvicorn app.api.server:app --reload --port 8000
```

The server will start at `http://127.0.0.1:8000`.

### API Endpoints

**Health Check:**
```bash
curl http://127.0.0.1:8000/health
```

**Process RINEX Files:**
```bash
curl -F "infile1=@sample_data/static_baseline/3076358x.25o" \
     -F "infile2=@sample_data/static_baseline/3075358x.25o" \
     -F "constellation=G" \
     http://127.0.0.1:8000/process
```

Response includes paths to generated figures:
```json
{
  "constellation": "G",
  "pairsProcessed": ["G10-G12", "G12-G23", ...],
  "outputs": {
    "diff_static": ["/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png", ...],
    "diffdiff_static": ["/static/diffdiff/ambiguity_diffdiff_G10_G12_L1_L2.png", ...]
  }
}
```

**View Generated Figures:**

Open in browser or download:
```bash
# View in browser
http://127.0.0.1:8000/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png

# Download with curl
curl -O http://127.0.0.1:8000/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png
```

**Interactive API Documentation:**
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc

For detailed API documentation, see [API_README.md](API_README.md).

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
