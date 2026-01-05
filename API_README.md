# GNSS Raw Ambiguity REST API

This API provides the functionality of `plot2sig.py` as a REST API. You can upload two RINEX observation files and generate ambiguity difference plots.

## Setup

### Install Dependencies

```bash
# Using uv (recommended)
uv sync

# Or traditional venv
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Starting the Server

### Using uv (recommended)

```bash
uv run uvicorn app.api.server:app --reload --port 8000
```

### Using traditional venv

```bash
source .venv/bin/activate
uvicorn app.api.server:app --reload --port 8000
```

The server will start at `http://127.0.0.1:8000`.

## Endpoints

### GET `/`
Returns basic API information.

```bash
curl http://127.0.0.1:8000/
```

### GET `/health`
Health check endpoint.

```bash
curl http://127.0.0.1:8000/health
```

**Response:**
```json
{"status": "ok"}
```

### POST `/process`
Processes two RINEX observation files and generates ambiguity plots.

**Parameters:**
- `infile1` (file, required): RINEX file from receiver 1
- `infile2` (file, required): RINEX file from receiver 2
- `constellation` (string, optional): Constellation identifier (default: "G")
  - `G`: GPS
  - `R`: GLONASS
  - `E`: Galileo
  - `C`: BeiDou
  - `J`: QZSS
  - `S`, `I`, `L`: Others
- `outdir` (string, optional): Output directory (default: "./outfigs")

**Example (using sample data):**

```bash
curl -F "infile1=@sample_data/static_baseline/3076358x.25o" \
     -F "infile2=@sample_data/static_baseline/3075358x.25o" \
     -F "constellation=G" \
     http://127.0.0.1:8000/process
```

**Response:**
```json
{
  "constellation": "G",
  "pairsProcessed": ["G10-G12", "G12-G23", "G23-G10", "G23-G24", "G24-G25", "G25-G23"],
  "outputs": {
    "diff": [
      "/home/user/gnssraw/outfigs/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png",
      ...
    ],
    "diff_static": [
      "/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png",
      ...
    ],
    "diffdiff": [
      "/home/user/gnssraw/outfigs/diffdiff/ambiguity_diffdiff_G10_G12_L1_L2.png",
      ...
    ],
    "diffdiff_static": [
      "/static/diffdiff/ambiguity_diffdiff_G10_G12_L1_L2.png",
      ...
    ]
  }
}
```

### GET `/static/{path}`
Static file endpoint to access generated plots.

**Examples:**
```bash
# Open in browser
http://127.0.0.1:8000/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png
http://127.0.0.1:8000/static/diffdiff/ambiguity_diffdiff_G10_G12_L1_L2.png

# Download with curl
curl -O http://127.0.0.1:8000/static/diff/ambiguity_diff_rec1_G10_G12_L1_L2.png
```

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc

## Troubleshooting

### `No module named 'encodings'` Error

If this error occurs, the virtual environment may be corrupted:

```bash
# Recreate the virtual environment
rm -rf .venv
uv venv
uv sync
```

### Port 8000 Already in Use

Specify a different port:

```bash
uv run uvicorn app.api.server:app --reload --port 8080
```

## Framework Comparison

### FastAPI (Current Implementation)
**Advantages:**
- Automatic API documentation generation (Swagger UI / ReDoc)
- Type validation with Pydantic
- Fast (Starlette/uvicorn)
- Modern and easy-to-use API
- Async support

**Disadvantages:**
- More dependencies

### Flask
Simple and lightweight, but type validation and documentation generation must be done manually.

```python
# Reference: Flask implementation example
from flask import Flask, request, jsonify
app = Flask(__name__)

@app.route('/process', methods=['POST'])
def process():
    file1 = request.files['infile1']
    file2 = request.files['infile2']
    # Process...
    return jsonify({"status": "ok"})
```

### Starlette
The foundation of FastAPI. Lower-level and more flexible, but you need to implement validation and documentation generation yourself.

### Sanic
Async-first and fast, but has a smaller community and ecosystem than FastAPI.

## Recommendation: Use FastAPI

**FastAPI** is ideal for data science/scientific computing applications:
- Type safety helps catch bugs early
- Automatic documentation makes sharing with other researchers easy
- Fast and handles large data processing
- Easy to call from Jupyter Notebooks and Python scripts
