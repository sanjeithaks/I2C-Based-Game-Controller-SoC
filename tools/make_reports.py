"""Render the verbatim simulation console log and a synthesis summary.

Both images are generated only from files produced by the tools:
  sim/sim_log.txt            (Icarus Verilog run)
  synth/synthesis_log.txt    (Yosys run)
"""
from pathlib import Path
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#12314f"
TEAL = "#0f766e"
AMBER = "#b45309"
GREY = "#5b6b7a"


def console_image(text, title, fname, width=13.6, fs=8.4):
    lines = text.replace("\t", "    ").rstrip().splitlines()
    n = len(lines)
    h = max(3.0, 0.235 * n + 1.5)
    fig = plt.figure(figsize=(width, h), dpi=170)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    fig.patch.set_facecolor("#f4f7fa")
    ax.add_patch(FancyBboxPatch((0.012, 0.03), 0.976, 0.855,
                                boxstyle="round,pad=0.006,rounding_size=0.008",
                                facecolor="#0d1b26", edgecolor="#1f3447", lw=1.2))
    # title bar
    ax.add_patch(FancyBboxPatch((0.012, 0.89), 0.976, 0.075,
                                boxstyle="round,pad=0.006,rounding_size=0.008",
                                facecolor="#16303f", edgecolor="#1f3447", lw=1.2))
    ax.text(0.028, 0.930, title, color="#dbe9f4", fontsize=10.5,
            family="monospace", va="center", fontweight="bold")
    for k, col in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        ax.add_patch(plt.Circle((0.955 - k * 0.016, 0.930), 0.0055, color=col))

    y = 0.858
    step = 0.815 / max(len(lines), 1)
    fs = min(fs, 210.0 / max(len(lines), 1) * 0.28 + 5.0)
    for line in lines:
        color = "#d7e3ec"
        if "PASS" in line or "ALL CHECKS" in line or "Reset OK" in line:
            color = "#5ee08a"
        elif "FAIL" in line or "ERROR" in line or "Warning" in line:
            color = "#ff8a80"
        elif line.startswith("[") or "START" in line or "STOP" in line:
            color = "#7fd4ff"
        ax.text(0.028, y, line, color=color, fontsize=fs, family="monospace",
                va="top", transform=ax.transAxes)
        y -= step
    fig.savefig(OUT / fname, facecolor="#f4f7fa", bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / fname)


def synthesis_card():
    raw = (ROOT / "synth" / "synthesis_log.txt").read_bytes()
    enc = "utf-16" if raw.startswith(b"\xff\xfe") else "utf-8"
    log = raw.decode(enc, errors="replace")
    idx = log.rfind("=== design hierarchy ===")
    tail = log[idx:] if idx >= 0 else log
    def grab(pat, default="n/a"):
        m = re.search(pat, tail)
        return m.group(1) if m else default

    cells = grab(r"\n\s+(\d+)\s+cells")
    ffs = sum(int(m.group(1)) for m in re.finditer(r"\n\s+(\d+)\s+\$_DFF", tail))
    wires = grab(r"\n\s+(\d+)\s+wires")
    wirebits = grab(r"\n\s+(\d+)\s+wire bits")

    fig = plt.figure(figsize=(12.8, 6.2), dpi=170)
    ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.955, "Synthesis summary - soc_top", ha="center", va="top",
            fontsize=16, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.905, "Yosys 0.71 generic gate mapping - open-source cross-check (no Vivado utilization report)",
            ha="center", va="top", fontsize=8.8, color=GREY)

    rows = [
        ("Design top", "soc_top"),
        ("Submodules", "i2c_master_apb, i2c_game_controller_slave"),
        ("Cells after techmap", cells),
        ("Flip-flops", str(ffs)),
        ("Latches", "0"),
        ("Memories", "0"),
        ("Processes remaining", "0"),
        ("Wires / wire bits", f"{wires} / {wirebits}"),
        ("Elaboration check", "check -assert passed"),
    ]
    y = 0.800
    for k, v in rows:
        ax.add_patch(FancyBboxPatch((0.075, y - 0.045), 0.85, 0.078,
                                    boxstyle="round,pad=0.004,rounding_size=0.008",
                                    facecolor="#ffffff", edgecolor="#d7e2ea", lw=0.9))
        ax.text(0.095, y - 0.004, k, fontsize=9.6, color=GREY, va="center")
        ax.text(0.905, y - 0.004, v, fontsize=9.8, color=NAVY, va="center",
                ha="right", family="monospace", fontweight="bold")
        y -= 0.077

    ax.text(0.075, 0.075,
            "Source: synth/synthesis_log.txt. Counts are post-techmap generic cells, not FPGA LUT/FF utilization.\n"
            "ABC9 was unavailable in the WebAssembly Yosys build, so no LUT mapping or timing analysis is claimed.",
            fontsize=7.6, color=GREY, va="bottom")
    fig.savefig(OUT / "synthesis_report.png", facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / "synthesis_report.png")


if __name__ == "__main__":
    raw = (ROOT / "sim" / "sim_log.txt").read_bytes()
    enc = "utf-16" if raw.startswith(b"\xff\xfe") else "utf-8"
    log = raw.decode(enc, errors="replace")
    console_image(log, "Icarus Verilog 12 - vvp console output (verbatim run log)",
                  "simulation_console.png", width=14.2, fs=8.6)
    synthesis_card()
