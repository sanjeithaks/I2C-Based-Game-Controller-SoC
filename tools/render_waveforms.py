"""Render professional waveform figures from the real Icarus Verilog VCD.

The VCD is parsed directly; every transition drawn comes from the simulation
database produced by testbench/tb_soc_top.v.
"""
from pathlib import Path
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

ROOT = Path(__file__).resolve().parents[1]
VCD = ROOT / "sim" / "dump.vcd"
OUT = ROOT / "docs" / "screenshots"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#12314f"
TEAL = "#0f766e"
AMBER = "#b45309"
RED = "#9f1239"
GREY = "#5b6b7a"
GRID = "#dfe7ee"


# --------------------------------------------------------------------------
# Minimal VCD reader
# --------------------------------------------------------------------------
def parse_vcd(path):
    names = {}
    values = {}
    scope = []
    t = 0
    with open(path, "r", errors="replace") as f:
        tokens = f.read().split()
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok == "$scope":
            scope.append(tokens[i + 2])
            i += 4
        elif tok == "$upscope":
            scope.pop()
            i += 2
        elif tok == "$var":
            # $var wire 8 ! name [7:0] $end
            width = int(tokens[i + 2])
            ident = tokens[i + 3]
            j = i + 4
            name = tokens[j]
            j += 1
            if tokens[j].startswith("["):
                j += 1
            full = ".".join(scope + [name])
            names[ident] = (full, width)
            values.setdefault(ident, [])
            i = j + 1
        elif tok.startswith("#"):
            t = int(tok[1:]) * 0.001   # VCD timescale is 1 ps -> ns
            i += 1
        elif tok in ("$dumpvars", "$dumpall", "$dumpoff", "$dumpon", "$end"):
            i += 1
        elif tok.startswith("$"):
            # skip metadata directives up to $end
            while i < len(tokens) and tokens[i] != "$end":
                i += 1
            i += 1
        else:
            if tok[0] in "01xzXZ":
                ident = tok[1:]
                values.setdefault(ident, []).append((t, tok[0]))
                i += 1
            elif tok[0] in "bB":
                bits = tok[1:]
                ident = tokens[i + 1]
                values.setdefault(ident, []).append((t, bits))
                i += 2
            else:
                i += 1
    return names, values


NAMES, VALUES = parse_vcd(VCD)


def lookup(suffix):
    hits = [(i, n) for i, (n, w) in NAMES.items() if n == suffix]
    if not hits:
        hits = [(i, n) for i, (n, w) in NAMES.items() if n.endswith("." + suffix)]
    if not hits:
        raise KeyError(suffix)
    ident = hits[0][0]
    return ident, NAMES[ident][1]


def to_int(bits):
    if any(c in "xzXZ" for c in bits):
        return None
    return int(bits, 2)


STATE_MASTER = {0: "IDLE", 1: "START", 2: "ADDR", 3: "ADDR_ACK",
                4: "READ", 5: "DATA_ACK", 6: "STOP", 7: "DONE"}
STATE_SLAVE = {0: "S_ADDR", 1: "S_ACK", 2: "S_DATA", 3: "S_IDLE"}


# --------------------------------------------------------------------------
# Drawing helpers
# --------------------------------------------------------------------------
def seg_list(changes):
    out = []
    for k, (t, v) in enumerate(changes):
        end = changes[k + 1][0] if k + 1 < len(changes) else 10 ** 18
        out.append((t, end, v))
    return out


def draw_wave(ax, sig, t0, t1, y, h=0.62, fmt="hex", color=TEAL, fs=7.0,
              min_label=18.0, states=None):
    ident, width = lookup(sig)
    ch = VALUES.get(ident, [])
    if not ch:
        return
    if width == 1:
        pts = [(t0, 1)]
        for t, v in ch:
            if t < t0:
                pts = [(t0, v)]
            elif t <= t1:
                pts.append((t, v))
        pts.append((t1, pts[-1][1]))
        ys = []
        for t, v in pts:
            hi = (v == "1")
            ys.append((t, y + (h / 2 if hi else -h / 2)))
        for k in range(len(ys) - 1):
            ax.plot([ys[k][0], ys[k + 1][0]], [ys[k][1], ys[k][1]],
                    color=color, lw=1.3, zorder=3)
            if ys[k][1] != ys[k + 1][1]:
                ax.plot([ys[k + 1][0], ys[k + 1][0]],
                        [ys[k][1], ys[k + 1][1]], color=color, lw=1.3, zorder=3)
        return

    segs = []
    prev_end = t0
    for t, e, v in seg_list(ch):
        if e <= t0 or t >= t1:
            continue
        s, en = max(t, t0), min(e, t1)
        segs.append((s, en, v))
        prev_end = en
    if not segs:
        return
    # merge consecutive identical values
    merged = []
    for s, e, v in segs:
        if merged and merged[-1][2] == v and abs(merged[-1][1] - s) < 1e-9:
            merged[-1] = (merged[-1][0], e, v)
        else:
            merged.append((s, e, v))
    slant = max((t1 - t0) * 0.003, 0.4)
    for s, e, v in merged:
        if e - s < slant * 1.2:
            continue
        iv = to_int(v) if len(v) > 1 else int(v, 2)
        if iv is None:
            text = "X"
        elif fmt == "state":
            table = states if states is not None else STATE_MASTER
            text = table.get(iv, str(iv))
        elif fmt == "dec":
            text = str(iv)
        elif fmt == "bin":
            text = format(iv, "0%db" % width)
        else:
            text = "0x%0*X" % ((width + 3) // 4, iv)
        poly = [(s + slant, y + h / 2), (e - slant, y + h / 2),
                (e, y), (e - slant, y - h / 2), (s + slant, y - h / 2),
                (s, y)]
        ax.add_patch(Polygon(poly, closed=True, facecolor="white",
                             edgecolor=color, lw=1.15, zorder=3))
        if (e - s) > min_label * (t1 - t0) / 1000.0:
            ax.text((s + e) / 2, y, text, ha="center", va="center",
                    fontsize=fs, color=color, zorder=4, family="monospace")


def figure(title, subtitle, rows, t0, t1, fname, note=None, figw=17.0):
    n = len(rows)
    fig, ax = plt.subplots(figsize=(figw, 2.2 + 0.44 * n), dpi=170)
    fig.subplots_adjust(left=0.215, right=0.985, top=1 - 0.95 / (2.2 + 0.44 * n),
                        bottom=1.15 / (2.2 + 0.44 * n))
    ax.set_xlim(t0, t1)
    ax.set_ylim(n + 0.2, 0.2)
    ax.set_yticks([])
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_xlabel("simulation time (ns)", fontsize=9, color=GREY)
    ax.tick_params(axis="x", labelsize=8, colors=GREY)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=1)
    ax.set_axisbelow(True)

    fig.text(0.012, 1 - 0.14 / (2.2 + 0.44 * n), title, fontsize=15.5,
             fontweight="bold", color=NAVY, va="top")
    fig.text(0.012, 1 - 0.42 / (2.2 + 0.44 * n), subtitle, fontsize=8.8,
             color=GREY, va="top")

    for idx, (label, sig, kw) in enumerate(rows):
        y = idx + 1
        ax.axhline(y, color=GRID, lw=0.6, zorder=1)
        ax.text(t0 - (t1 - t0) * 0.012, y, label, ha="right", va="center",
                fontsize=8.4, color=NAVY, family="monospace", clip_on=False)
        kw = dict(kw)
        if "color" not in kw:
            kw["color"] = TEAL
        draw_wave(ax, sig, t0, t1, y, **kw)

    if note:
        fig.text(0.012, 0.010, note, fontsize=8.0, color=GREY, va="bottom")
    fig.savefig(OUT / fname, facecolor="white", bbox_inches="tight")
    plt.close(fig)
    print("wrote", OUT / fname)


def main():
    all_t = [t for ch in VALUES.values() for t, _ in ch]
    tend = max(all_t)
    print("VCD end time:", tend, "ns")

    figure(
        "I2C Game Controller SoC - full transaction waveform",
        "Icarus Verilog 12 simulation of testbench/tb_soc_top.v  |  dump.vcd  |  clock = 100 MHz",
        [
            ("reset",            "reset",                dict(h=0.55, color=RED)),
            ("apb_start",        "apb_start",            dict(h=0.55, color=NAVY)),
            ("apb_done",         "master.apb_done",         dict(h=0.55, color=AMBER)),
            ("scl",              "scl",                  dict(h=0.55, color=NAVY)),
            ("sda",              "sda",                  dict(h=0.55, color=TEAL)),
            ("slave_addr[6:0]",  "slave_addr",           dict(fmt="hex", color=TEAL)),
            ("controller_buttons[7:0]", "controller_buttons", dict(fmt="hex", color=AMBER)),
            ("button_status[7:0]", "button_status",      dict(fmt="hex", color=TEAL)),
            ("master.state[2:0]", "dut.master.state",    dict(fmt="state", color=AMBER, h=0.55)),
            ("slave.state[1:0]",  "dut.slave.state",     dict(fmt="state", color=AMBER, h=0.55, states=STATE_SLAVE)),
        ],
        0, tend, "simulation_waveform.png",
        note="All values are read directly from the simulation VCD. Three APB reads are performed: two addressed reads and one NACK test.",
    )

    figure(
        "I2C bus detail - START, address, ACK and data",
        "Zoom of transaction 1 (slave address 0x42, controller_buttons = 0xAC)  |  SCL period = 80 ns",
        [
            ("scl",             "scl",                 dict(h=0.6, color=NAVY)),
            ("sda",             "sda",                 dict(h=0.6, color=TEAL)),
            ("master.state",    "dut.master.state",    dict(fmt="state", color=AMBER, h=0.58)),
            ("slave.state",     "dut.slave.state",     dict(fmt="state", color=AMBER, h=0.58, states=STATE_SLAVE)),
            ("bit_cnt[3:0]",    "dut.master.bit_cnt",  dict(fmt="dec", color=GREY, h=0.5)),
            ("shift_reg[7:0]",  "dut.master.shift_reg", dict(fmt="hex", color=TEAL)),
            ("addr_match",      "dut.slave.addr_match", dict(h=0.55, color=AMBER)),
            ("sda_drive",       "dut.slave.sda_drive", dict(h=0.55, color=GREY)),
        ],
        60, 1620, "i2c_communication.png",
        note="START at 65 ns (SDA falls while SCL is high). The master shifts {0x42, R/W=1}; the addressed slave drives ACK low on the 9th clock.",
        figw=18.0,
    )

    figure(
        "FSM and datapath during a complete read",
        "Master and slave state transitions aligned with SCL/SDA (transaction 1)",
        [
            ("scl",             "scl",                 dict(h=0.55, color=NAVY)),
            ("sda",             "sda",                 dict(h=0.55, color=TEAL)),
            ("master.state",    "dut.master.state",    dict(fmt="state", color=AMBER)),
            ("slave.state",     "dut.slave.state",     dict(fmt="state", color=AMBER, states=STATE_SLAVE)),
            ("bit_cnt[3:0]",    "dut.master.bit_cnt",  dict(fmt="dec", color=GREY, h=0.5)),
            ("shift_reg[7:0]",  "dut.master.shift_reg", dict(fmt="hex", color=TEAL)),
            ("apb_data_out[7:0]", "dut.master.apb_data_out", dict(fmt="hex", color=TEAL)),
        ],
        40, 1660, "fsm_transitions.png",
        note="IDLE -> START -> ADDR -> ADDR_ACK -> READ -> DATA_ACK -> STOP -> DONE. shift_reg accumulates MSB first and is published on completion.",
        figw=18.0,
    )

    figure(
        "Final result - received button state and APB completion",
        "End of transaction 1: apb_done pulses, button_status[7:0] = 0xAC",
        [
            ("clk",                "clk",                  dict(h=0.5, color=GREY)),
            ("apb_start",          "apb_start",            dict(h=0.55, color=NAVY)),
            ("apb_done",           "master.apb_done",         dict(h=0.55, color=AMBER)),
            ("controller_buttons[7:0]", "controller_buttons", dict(fmt="hex", color=AMBER)),
            ("button_status[7:0]", "button_status",        dict(fmt="hex", color=TEAL)),
            ("scl",                "scl",                  dict(h=0.55, color=NAVY)),
            ("sda",                "sda",                  dict(h=0.55, color=TEAL)),
        ],
        1490, 1680, "final_output.png",
        note="Received byte 0xAC equals controller_buttons[7:0]; apb_done is a one-cycle completion pulse.",
        figw=16.0,
    )


if __name__ == "__main__":
    main()
