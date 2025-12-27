"""
Plot Pseudorange and carrier phase from RINEX observation file.

"""

import georinex as gr
import warnings
from logging import getLogger, basicConfig, INFO

import matplotlib as mpl
import matplotlib.pyplot as plt

logger = getLogger(__name__)
basicConfig(level=INFO, format="%(asctime)s %(levelname)s %(message)s")


def plot_observables(rnxobs, satname: str, outfile: str = "obs.png"):
    ax = plt.gca()
    ax.plot(rnxobs.time, rnxobs["C1C"].sel(sv=satname))
    ax.set_xlabel("GPS time")
    ax.set_ylabel("Pseudorange [m]")
    ax.grid(True)

    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)
    axes[0].plot(rnxobs.time, rnxobs["C1C"].sel(sv=satname), label=satname)
    axes[1].plot(rnxobs.time, rnxobs["L1C"].sel(sv=satname), label=satname)
    axes[2].plot(rnxobs.time, rnxobs["D1C"].sel(sv=satname), label=satname)
    axes[3].plot(rnxobs.time, rnxobs["S1C"].sel(sv=satname), label=satname)

    axes[0].set_title("Pseudo range[m]")
    axes[0].set_ylabel(r"$\rho$ [m]")
    axes[1].set_title("carrier phase")
    axes[1].set_ylabel(r"$\phi$ [cycle]")
    axes[2].set_title("Doppler frequency")
    axes[2].set_ylabel("D[Hz]")
    axes[3].set_title("C/N0")
    axes[3].set_ylabel("S [dB]")
    for a in axes:
        a.grid(True)

    axes[3].set_xlabel("GPST")
    plt.tight_layout()
    plt.savefig(outfile)
    return fig, axes


CLIGHT = 299792458.0
L1_FREQ = 1.57542e9
L2_FREQ = 1.22760e9
L5_FREQ = 1.17645e9
wlen_L1 = CLIGHT / L1_FREQ
wlen_L2 = CLIGHT / L2_FREQ
wlen_L5 = CLIGHT / L5_FREQ
print(f"wlen_L1: {wlen_L1}, wlen_L2: {wlen_L2}, wlen_L5: {wlen_L5}")


def plot_pr_cp(ax, rnxobs, freq=""):
    if freq == "L1":
        wlen = wlen_L1
        cp = rnxobs["L1C"].sel(sv=satname)
        pr = rnxobs["C1C"].sel(sv=satname)
        dp = rnxobs["D1C"].sel(sv=satname)
    elif freq == "L2":
        wlen = wlen_L2
        cp = rnxobs["L2X"].sel(sv=satname)
        pr = rnxobs["C2X"].sel(sv=satname)
        dp = rnxobs["D2X"].sel(sv=satname)
    elif freq == "L5":
        wlen = wlen_L5
        cp = rnxobs["L5X"].sel(sv=satname)
        pr = rnxobs["C5X"].sel(sv=satname)
        dp = rnxobs["D5X"].sel(sv=satname)
    else:
        raise ValueError("freq must be L1, L2, or L5")
    cp_pr = cp - pr / wlen
    # caluclate doppler - difference of carrier phase
    b2 = cp.diff("time") * (1 / 30.0) + dp

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    plt.suptitle(f"Analysis of Raw Measurement ({satname})")
    axes[0].set_title(r"$-N - \frac{2}{\lambda}I$")
    axes[0].plot(rnxobs.time, cp_pr)
    axes[0].set_ylabel("CP-PR")

    axes[1].set_title(r"$\frac{1}{\lambda}(I + d/dt (I+T))$")
    axes[1].plot(b2.time, b2)
    axes[1].set_ylabel("DP - CP")
    x = cp_pr + 2.0 * b2

    axes[2].set_title(r"$N$")
    axes[2].plot(x.time, -x.values)
    axes[2].set_ylabel("bias [cycle]")
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    return fig, axes


def plot_widelane_ambiguity(ax, rnxobs):
    pr_l1 = rnxobs["C1C"].sel(sv=satname)
    cp_l1 = rnxobs["L1C"].sel(sv=satname)
    pr_l2 = rnxobs["C2X"].sel(sv=satname)
    cp_l2 = rnxobs["L2X"].sel(sv=satname)
    time = rnxobs.time
    # Wide-lane (phase): L1 - L2
    wl_cp = cp_l1 - cp_l2
    wl_wlen = CLIGHT / (L1_FREQ - L2_FREQ)
    # Narrow-lane (code): L1 + L2
    nl_pr = (
        L1_FREQ / (L1_FREQ + L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ + L2_FREQ) * pr_l2
    )

    # Narrow-lane (phase): L1 + L2
    nl_cp = cp_l1 + cp_l2
    # wide-lane (code): L1 - L2
    wl_pr = (
        L1_FREQ / (L1_FREQ - L2_FREQ) * pr_l1 + L2_FREQ / (L1_FREQ - L2_FREQ) * pr_l2
    )
    nl_wlen = CLIGHT / (L1_FREQ + L2_FREQ)
    logger.debug(f"wide lane {wl_wlen * 100} cm narrow-lane {nl_wlen * 100} cm")

    fig, axes = plt.subplots(4, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, wl_cp - nl_pr / wl_wlen)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Narrow-lane Ambiguity $N_{L1} + N_{L2} + ERROR$")
    axes[1].plot(time, nl_cp - wl_pr / wl_wlen)
    axes[1].set_ylabel("NL CP - PR [m]")

    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    plt.tight_layout()
    return fig, axes


infile = "./3019148c.23o"
warnings.simplefilter("ignore", FutureWarning)
rnxobs = gr.load(infile)
print(rnxobs)


# target satellite and initial observables plot
satname = "G27"
fig, axes = plot_observables(rnxobs, satname, outfile="obs.png")


fig, axes = plot_pr_cp(plt.gca(), rnxobs, freq="L1")
out_figfile = f"bias_analysis_L1_{satname}_L1.png"
plt.savefig(out_figfile)

fig, axes = plot_pr_cp(plt.gca(), rnxobs, freq="L2")
out_figfile = f"bias_analysis_L2_{satname}_L2.png"
plt.savefig(out_figfile)

fig, axes = plot_pr_cp(plt.gca(), rnxobs, freq="L5")
out_figfile = f"bias_analysis_L5_{satname}_L5.png"
plt.savefig(out_figfile)

fig, axes = plot_widelane_ambiguity(plt.gca(), rnxobs)
out_figfile = f"wide_narrow_lane_{satname}_L1_L2.png"
plt.savefig(out_figfile)

# Only show interactively when not using headless Agg backend
if mpl.get_backend() != "Agg":
    plt.show()
