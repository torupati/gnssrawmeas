from pathlib import Path
from typing import List, Dict, Tuple
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

import warnings
import georinex as gr
import matplotlib.pyplot as plt

from app.plot2sig import plot_ambiguity_diff, plot_ambiguity_diff2


DEFAULT_OUTDIR = Path("./outfigs")


app = FastAPI(title="GNSS Raw Ambiguity API", version="0.1.0")

# Allow simple local testing from browsers/tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists and mount for serving generated images
DEFAULT_OUTDIR.mkdir(parents=True, exist_ok=True)
(DEFAULT_OUTDIR / "single").mkdir(parents=True, exist_ok=True)
(DEFAULT_OUTDIR / "diff").mkdir(parents=True, exist_ok=True)
(DEFAULT_OUTDIR / "diffdiff").mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(DEFAULT_OUTDIR)), name="static")


def _save_upload(upload: UploadFile, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    out_path = target_dir / upload.filename
    with out_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return out_path


def _detect_satellites(rnxobs1, rnxobs2, constellation_prefix: str) -> List[str]:
    try:
        sv_values = [str(s) for s in rnxobs1.sv.values + rnxobs2.sv.values]
        sv_values = list(set(sv_values))
    except Exception:
        sv_values = [str(s) for s in rnxobs1.coords.get("sv", []).values]

    satname_list = sorted(
        [s for s in sv_values if s.startswith(constellation_prefix)],
        key=lambda x: (x[0], int(x[1:]) if x[1:].isdigit() else 999),
    )
    return satname_list


def _valid_pair_in_both(rnxobs1, rnxobs2, satname: str) -> bool:
    return satname in [str(s) for s in rnxobs1.sv.values] and satname in [
        str(s) for s in rnxobs2.sv.values
    ]


def process_rinex_and_generate(
    rnxobs1, rnxobs2, constellation: str, outdir: Path, sat_pairs: List[Tuple[str, str]]
) -> Dict[str, List[str]]:
    warnings.simplefilter("ignore", FutureWarning)

    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "single").mkdir(parents=True, exist_ok=True)
    (outdir / "diff").mkdir(parents=True, exist_ok=True)
    (outdir / "diffdiff").mkdir(parents=True, exist_ok=True)

    saved_diff: List[str] = []
    saved_diffdiff: List[str] = []

    for satname1, satname2 in sat_pairs:
        # Verify presence in both files
        if not (
            _valid_pair_in_both(rnxobs1, rnxobs2, satname1)
            and _valid_pair_in_both(rnxobs1, rnxobs2, satname2)
        ):
            continue

        # Receiver 1 single-difference
        fig1, _ = plot_ambiguity_diff(rnxobs1, satname1, satname2)
        outfile1 = (
            outdir / "diff" / f"ambiguity_diff_rec1_{satname1}_{satname2}_L1_L2.png"
        )
        fig1.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig1.tight_layout(rect=(0, 0.03, 1, 0.95))
        fig1.savefig(outfile1)
        plt.close(fig1)
        saved_diff.append(str(outfile1))

        # Receiver 2 single-difference
        fig2, _ = plot_ambiguity_diff(rnxobs2, satname1, satname2)
        outfile2 = (
            outdir / "diff" / f"ambiguity_diff_rec2_{satname1}_{satname2}_L1_L2.png"
        )
        fig2.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig2.tight_layout(rect=(0, 0.03, 1, 0.95))
        fig2.savefig(outfile2)
        plt.close(fig2)
        saved_diff.append(str(outfile2))

        # Double-difference
        fig3, _ = plot_ambiguity_diff2(rnxobs1, rnxobs2, satname1, satname2)
        outfile3 = (
            outdir / "diffdiff" / f"ambiguity_diffdiff_{satname1}_{satname2}_L1_L2.png"
        )
        fig3.suptitle(f"Satellite Single Difference {satname1} vs {satname2}")
        fig3.tight_layout(rect=(0, 0.03, 1, 0.95))
        fig3.savefig(outfile3)
        plt.close(fig3)
        saved_diffdiff.append(str(outfile3))

    return {"diff": saved_diff, "diffdiff": saved_diffdiff}


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/process")
async def process(
    infile1: UploadFile = File(...),
    infile2: UploadFile = File(...),
    constellation: str = Form("G"),
    outdir: str = Form(str(DEFAULT_OUTDIR)),
):
    """Process two RINEX observation files and generate ambiguity figures.

    Returns lists of generated figure paths under `diff` and `diffdiff`.
    Files are served via `/static/...` when using default outdir.
    """

    # Basic validation
    if constellation not in {"G", "R", "E", "C", "J", "S", "I", "L"}:
        raise HTTPException(status_code=400, detail="Invalid constellation prefix")

    uploads_dir = Path("./uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # Save uploads to disk
    f1_path = _save_upload(infile1, uploads_dir)
    f2_path = _save_upload(infile2, uploads_dir)

    # Load with georinex
    try:
        warnings.simplefilter("ignore", FutureWarning)
        rnxobs1 = gr.load(str(f1_path))
        rnxobs2 = gr.load(str(f2_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load RINEX: {e}")

    # Determine satellite pairs: use defaults similar to script for GPS; otherwise make adjacent pairs
    satname_list = _detect_satellites(rnxobs1, rnxobs2, constellation)
    if not satname_list:
        raise HTTPException(
            status_code=404, detail="No satellites found for constellation"
        )

    if constellation == "G":
        default_pairs = [
            ("G10", "G12"),
            ("G12", "G23"),
            ("G23", "G10"),
            ("G23", "G24"),
            ("G24", "G25"),
            ("G25", "G23"),
        ]
    elif constellation == "J":
        default_pairs = [("J02", "J03"), ("J03", "J07"), ("J07", "J02")]
    else:
        # Create adjacent pairs for detected satellites of this constellation
        csats = satname_list
        default_pairs = [(csats[i], csats[i + 1]) for i in range(len(csats) - 1)]

    out_dir_path = Path(outdir)

    outputs = process_rinex_and_generate(
        rnxobs1=rnxobs1,
        rnxobs2=rnxobs2,
        constellation=constellation,
        outdir=out_dir_path,
        sat_pairs=default_pairs,
    )

    # Build static URLs when under default mount
    def to_static_url(path_str: str) -> str:
        try:
            p = Path(path_str).resolve()
            base = DEFAULT_OUTDIR.resolve()
            rel = p.relative_to(base)
            return f"/static/{rel.as_posix()}"
        except Exception:
            return path_str

    resp = {
        "constellation": constellation,
        "pairsProcessed": [f"{a}-{b}" for a, b in default_pairs],
        "outputs": {
            "diff": outputs["diff"],
            "diff_static": [to_static_url(p) for p in outputs["diff"]],
            "diffdiff": outputs["diffdiff"],
            "diffdiff_static": [to_static_url(p) for p in outputs["diffdiff"]],
        },
    }

    return JSONResponse(resp)


# Optional root endpoint for quick info
@app.get("/")
def root():
    return {
        "name": "GNSS Raw Ambiguity API",
        "health": "/health",
        "process": "/process (POST multipart/form-data)",
        "static": "/static (mounted to outfigs)",
    }
