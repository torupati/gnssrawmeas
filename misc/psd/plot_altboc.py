from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from plot_boc import boc_acf, boc_psd
from scipy.signal import welch

F0 = 1.023  # base chip rate (MHz)
FS = 15 * F0  # AltBOC subcarrier frequency (MHz)
FC = 10 * F0  # E5 code chip rate (MHz)


def altboc_psd(freq: np.ndarray, fs: float = FS, fc: float = FC) -> np.ndarray:
    """Constant-envelope AltBOC(15,10) PSD, normalised to unit total power (1/MHz).

    Closed form for odd 2fs/fc (Rebeyrol et al., ION NTM 2005), divided by 8 so that
    the integral over all frequencies is 1:
    G(f) = fc / (2 (πf)²) · cos²(πf/fc) / cos²(πf/(2fs))
           · [cos²(πf/(2fs)) - cos(πf/(2fs)) - 2 cos(πf/(2fs)) cos(πf/(4fs)) + 2]
    """
    # the bracket term is O(f²) near DC, so a tiny eps loses it to cancellation
    eps = 1e-4
    f_safe = np.where(np.abs(freq) < eps, eps, freq)
    # cos(πf/fc) and cos(πf/(2fs)) vanish together at f = ±fs, ±3fs, ... (removable 0/0)
    f_safe = np.where(np.abs(np.cos(np.pi * f_safe / (2 * fs))) < 1e-6, f_safe + eps, f_safe)
    x = np.pi * f_safe
    c2 = np.cos(x / (2 * fs))
    c4 = np.cos(x / (4 * fs))
    return fc / (2 * x**2) * np.cos(x / fc) ** 2 / c2**2 * (c2**2 - c2 - 2 * c2 * c4 + 2)


def altboc_waveform(n_chips: int, samples_per_eighth: int = 16, seed: int = 0) -> tuple[np.ndarray, np.ndarray, float]:
    """Simulate the Galileo E5 AltBOC(15,10) baseband signal (OS SIS ICD definition).

    Four random ±1 codes (E5a-I, E5a-Q, E5b-I, E5b-Q) are multiplexed with the
    single (scS) and product (scP) subcarriers into a constant-envelope 8-PSK signal.
    Returns (signal, E5a code eA_I + j eA_Q, sampling rate in MHz).
    """
    fsamp = 8 * samples_per_eighth * FS  # 8 subcarrier phases per period
    spc = round(fsamp / FC)  # samples per chip (1.5 subcarrier periods per chip)
    t = np.arange(n_chips * spc) / fsamp
    w = 2 * np.pi * FS * t + 1e-9  # offset keeps samples off the sign transitions

    def sgn(v: np.ndarray) -> np.ndarray:
        return np.where(v >= 0, 1.0, -1.0)

    r2 = np.sqrt(2) / 4
    sc_s = r2 * sgn(np.cos(w - np.pi / 4)) + 0.5 * sgn(np.cos(w)) + r2 * sgn(np.cos(w + np.pi / 4))
    sc_p = -r2 * sgn(np.cos(w - np.pi / 4)) + 0.5 * sgn(np.cos(w)) - r2 * sgn(np.cos(w + np.pi / 4))
    quarter = 2 * samples_per_eighth  # Ts/4 delay
    sc_s_d = np.roll(sc_s, quarter)
    sc_p_d = np.roll(sc_p, quarter)

    rng = np.random.default_rng(seed)
    a_i, a_q, b_i, b_q = (np.repeat(c, spc) for c in rng.choice([-1.0, 1.0], size=(4, n_chips)))
    # product signals that keep the envelope constant
    pa_i, pa_q = a_q * b_i * b_q, a_i * b_i * b_q
    pb_i, pb_q = b_q * a_i * a_q, b_i * a_i * a_q

    s = (
        (a_i + 1j * a_q) * (sc_s - 1j * sc_s_d)
        + (b_i + 1j * b_q) * (sc_s + 1j * sc_s_d)
        + (pa_i + 1j * pa_q) * (sc_p - 1j * sc_p_d)
        + (pb_i + 1j * pb_q) * (sc_p + 1j * sc_p_d)
    ) / (2 * np.sqrt(2))
    return s, a_i + 1j * a_q, fsamp


def circular_xcorr(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """R[k] = mean(x[n + k] · conj(y[n])), returned with zero lag at the centre."""
    r = np.fft.ifft(np.fft.fft(x) * np.conj(np.fft.fft(y))) / len(x)
    return np.fft.fftshift(r)


def plot_altboc(bw_mhz: float = 50.0) -> None:
    s, code_a, fsamp = altboc_waveform(n_chips=8000)
    print(f"Envelope |s|: min {np.abs(s).min():.6f}, max {np.abs(s).max():.6f}")

    freq = np.linspace(-bw_mhz, bw_mhz, 8001)
    f_sim, p_sim = welch(s, fs=fsamp, nperseg=2**14, detrend=False, return_onesided=False, scaling="density")
    f_sim, p_sim = np.fft.fftshift(f_sim), np.fft.fftshift(p_sim)
    in_band = np.abs(f_sim) <= bw_mhz

    # BOC(15,10) rescaled to unit power for an equal-power comparison
    f_wide = np.linspace(-2000, 2000, 2_000_001)
    psd_boc = boc_psd(freq, 15, 10, F0) / np.trapezoid(boc_psd(f_wide, 15, 10, F0), f_wide)

    # ACFs versus τ/Tc
    lag = (np.arange(len(s)) - len(s) // 2) / fsamp * FC
    view = np.abs(lag) <= 2
    acf_full = circular_xcorr(s, s).real
    t = np.arange(len(s)) / fsamp
    # single-sideband E5a processing: BPSK(10) replica shifted down to -fs
    replica_a = code_a * np.exp(-2j * np.pi * FS * t) / np.sqrt(2)
    acf_e5a = np.abs(circular_xcorr(s, replica_a))
    tau_norm = np.linspace(-2, 2, 2000)
    acf_boc = boc_acf(15, 10, tau_norm)

    def to_db(psd: np.ndarray) -> np.ndarray:
        return 10 * np.log10(psd + 1e-12)

    fig, (ax_psd, ax_acf) = plt.subplots(1, 2, figsize=(16, 6))
    fig.suptitle("Galileo E5 AltBOC(15,10): constant-envelope 8-PSK", fontsize=13)

    ax_psd.plot(f_sim[in_band], to_db(p_sim[in_band]), color="gray", lw=0.8, alpha=0.7, label="AltBOC simulated (Welch)")
    ax_psd.plot(freq, to_db(altboc_psd(freq)), color="darkviolet", lw=2.0, label="AltBOC(15,10) closed form")
    ax_psd.plot(freq, to_db(psd_boc), color="purple", lw=1.5, linestyle="--", label="BOC(15,10) (same power)")
    ax_psd.axvline(x=-FS, color="crimson", linestyle=":", alpha=0.6, label="E5a (1176.45 MHz)")
    ax_psd.axvline(x=FS, color="royalblue", linestyle=":", alpha=0.6, label="E5b (1207.14 MHz)")
    ax_psd.set_title("Power Spectral Density (unit total power)", fontsize=12)
    ax_psd.set_xlabel("Frequency Offset from E5 Centre 1191.795 MHz (MHz)", fontsize=11)
    ax_psd.set_ylabel("PSD (dB/MHz)", fontsize=11)
    ax_psd.set_xlim(-bw_mhz, bw_mhz)
    ax_psd.set_ylim(-60, -10)
    ax_psd.grid(True, which="both", linestyle=":", alpha=0.5)
    ax_psd.legend(loc="lower center", fontsize=9)

    ax_acf.plot(lag[view], acf_full[view], color="darkviolet", lw=1.5, label="AltBOC full-band (real part)")
    ax_acf.plot(lag[view], acf_e5a[view], color="crimson", lw=2.0, label="E5a single-sideband |R|")
    ax_acf.plot(tau_norm, acf_boc, color="purple", lw=1.2, linestyle="--", label="BOC(15,10)")
    ax_acf.axhline(y=0, color="black", linestyle="--", alpha=0.6)
    ax_acf.set_title("Autocorrelation Function", fontsize=12)
    ax_acf.set_xlabel(r"Normalised Delay $\tau\,/\,T_c$  ($T_c = 1/10.23\,\mu s$)", fontsize=11)
    ax_acf.set_ylabel("Normalized Correlation", fontsize=11)
    ax_acf.set_xlim(-2, 2)
    ax_acf.set_ylim(-0.8, 1.1)
    ax_acf.grid(True, which="both", linestyle=":", alpha=0.5)
    ax_acf.legend(loc="upper right", fontsize=9)

    print(f"E5a single-sideband correlation peak: {acf_e5a.max():.3f}")
    first_neg = acf_full[len(s) // 2 :].argmin()
    print(f"Full-band ACF deepest sidelobe: {acf_full[len(s) // 2 + first_neg]:.3f} at τ/Tc = {lag[len(s) // 2 + first_neg]:.3f}")

    plt.tight_layout()
    figname = Path(__file__).resolve().parents[2] / "doc" / "figures" / "galileo_altboc_psd_acf.png"
    plt.savefig(figname, dpi=300)
    print(f"Saved figure: {figname}")
    plt.show()


if __name__ == "__main__":
    plot_altboc()
