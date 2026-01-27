import logging

import matplotlib.pyplot as plt
from georinex import rinexobs


from app.gnss.satellite_signals import get_available_signal_code
from app.gnss.constants import wlen_L1, wlen_L2, wlen_L5, CLIGHT, L1_FREQ, L2_FREQ
from app.gnss.ambiguity import (
    get_widelane_ambiguity,
    get_narrowlane_ambiguity,
)

logger = logging.getLogger(__name__)


def plot_observables(rnxobs, satname: str, outfile: str = "obs.png"):
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
    fig.tight_layout()
    fig.savefig(outfile)
    return fig, axes


def plot_pr_cp(rnxobs, satname: str, freq=""):
    if freq == "L1":
        wlen = wlen_L1
        # Dynamically detect available L1 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L1")
        if signal_code is None:
            logger.warning(
                f"No L1 signal available for {satname}, skipping L1 analysis"
            )
            return None, None
        logger.info(f"Using L1{signal_code} signal for {satname}")
        cp = rnxobs[f"L1{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C1{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D1{signal_code}"].sel(sv=satname)
    elif freq == "L2":
        wlen = wlen_L2
        # Dynamically detect available L2 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L2")
        if signal_code is None:
            logger.warning(
                f"No L2 signal available for {satname}, skipping L2 analysis"
            )
            return None, None
        logger.info(f"Using L2{signal_code} signal for {satname}")
        cp = rnxobs[f"L2{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C2{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D2{signal_code}"].sel(sv=satname)
    elif freq == "L5":
        wlen = wlen_L5
        # Dynamically detect available L5 signal code
        signal_code = get_available_signal_code(rnxobs, satname, "L5")
        if signal_code is None:
            logger.warning(
                f"No L5 signal available for {satname}, skipping L5 analysis"
            )
            return None, None
        logger.info(f"Using L5{signal_code} signal for {satname}")
        cp = rnxobs[f"L5{signal_code}"].sel(sv=satname)
        pr = rnxobs[f"C5{signal_code}"].sel(sv=satname)
        dp = rnxobs[f"D5{signal_code}"].sel(sv=satname)
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
    fig.suptitle(f"Analysis of Raw Measurement ({satname})")
    fig.tight_layout(rect=(0, 0.03, 1, 0.95))
    return fig, axes


def plot_ionofree_combination(rnxobs, satname: str):
    # Dynamically detect available L1 signal code
    l1_signal_code = get_available_signal_code(rnxobs, satname, "L1")
    if l1_signal_code is None:
        logger.warning(
            f"No L1 signal available for {satname}, cannot compute iono-free combination"
        )
        return None, None

    # Dynamically detect available L2 signal code
    l2_signal_code = get_available_signal_code(rnxobs, satname, "L2")
    if l2_signal_code is None:
        logger.warning(
            f"No L2 signal available for {satname}, cannot compute iono-free combination"
        )
        return None, None

    logger.info(
        f"Computing iono-free combination using L1{l1_signal_code} and L2{l2_signal_code} for {satname}"
    )

    pr_l1 = rnxobs[f"C1{l1_signal_code}"].sel(sv=satname)
    cp_l1 = rnxobs[f"L1{l1_signal_code}"].sel(sv=satname)
    pr_l2 = rnxobs[f"C2{l2_signal_code}"].sel(sv=satname)
    cp_l2 = rnxobs[f"L2{l2_signal_code}"].sel(sv=satname)
    time = rnxobs.time
    # Iono-free combination
    pr_if = (L1_FREQ**2 * pr_l1 - L2_FREQ**2 * pr_l2) / (L1_FREQ**2 - L2_FREQ**2)
    cp_if = (L1_FREQ**2 * wlen_L1 * cp_l1 - L2_FREQ**2 * wlen_L2 * cp_l2) / (
        L1_FREQ**2 - L2_FREQ**2
    )
    wlen_if = CLIGHT / (L1_FREQ**2 - L2_FREQ**2) * (L1_FREQ + L2_FREQ)

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title("Iono-free Pseudorange and Carrier Phase")
    axes[0].plot(time, pr_if, label="Pseudorange IF")
    axes[0].plot(time, cp_if * wlen_if, label="Carrier Phase IF")
    axes[0].set_ylabel("Pseudorange / Carrier Phase [m]")
    axes[0].legend()

    axes[1].set_title(r"Carrier Phase - Pseudorange")
    axes[1].plot(time, cp_if - pr_if)
    axes[1].set_ylabel("CP - PR [m]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(
        time, rnxobs[f"S1{l1_signal_code}"].sel(sv=satname), label=f"S1{l1_signal_code}"
    )
    axes[2].plot(
        time, rnxobs[f"S2{l2_signal_code}"].sel(sv=satname), label=f"S2{l2_signal_code}"
    )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    fig.tight_layout()
    return fig, axes


def plot_ambiguity_single_sat_single_rec(rnxobs: rinexobs, satname: str):
    # Dynamically detect available L1 signal code
    l1_signal_code = get_available_signal_code(rnxobs, satname, "L1")
    if l1_signal_code is None:
        logger.warning(
            f"No L1 signal available for {satname}, cannot compute ambiguity"
        )
        return None, None

    # Dynamically detect available L2 signal code
    l2_signal_code = get_available_signal_code(rnxobs, satname, "L2")
    if l2_signal_code is None:
        logger.warning(
            f"No L2 signal available for {satname}, cannot compute ambiguity"
        )
        return None, None

    logger.info(
        f"Computing ambiguity using L1{l1_signal_code} and L2{l2_signal_code} for {satname}"
    )

    time = rnxobs.time
    amb_wl = get_widelane_ambiguity(
        rnxobs,
        satname,
        f"C1{l1_signal_code}",
        f"L1{l1_signal_code}",
        f"C2{l2_signal_code}",
        f"L2{l2_signal_code}",
    )
    # Use the time-average of the wide-lane ambiguity in downstream computation
    amb_wl_mean = float(amb_wl.mean().values)

    # Iono-free combination
    amb_n1 = get_narrowlane_ambiguity(
        rnxobs,
        satname,
        amb_wl_mean,
        f"C1{l1_signal_code}",
        f"L1{l1_signal_code}",
        f"C2{l2_signal_code}",
        f"L2{l2_signal_code}",
    )

    fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
    axes[0].set_title(r"Wide-lane Ambiguity $N_{L1} - N_{L2}$")
    axes[0].plot(time, amb_wl)
    axes[0].set_ylabel(r"$B_{wl}$ [cycle]")

    axes[1].set_title(r"Ambiguity $N_{L1}$")
    axes[1].plot(time, amb_n1)
    axes[1].set_ylabel("Ambiguity $N_{L1}$ [cycle]")

    axes[2].set_title("Signal Strength")
    axes[2].plot(
        time, rnxobs[f"S1{l1_signal_code}"].sel(sv=satname), label=f"S1{l1_signal_code}"
    )
    axes[2].plot(
        time, rnxobs[f"S2{l2_signal_code}"].sel(sv=satname), label=f"S2{l2_signal_code}"
    )
    axes[2].set_ylabel("C/N0 [dB-Hz]")
    axes[2].legend()
    for ax in axes:
        ax.grid(True)
    axes[2].set_xlabel("GPST")
    axes[2].set_xlim(time[0], time[-1])
    fig.suptitle(f"Satellite {satname}", y=1.02)
    plt.tight_layout()
    return fig, axes
