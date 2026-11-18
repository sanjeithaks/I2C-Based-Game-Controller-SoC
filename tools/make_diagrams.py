"""Generate project diagrams from the actual RTL structure.

Outputs (docs/architecture):
  architecture.png   block diagram of soc_top and its two RTL blocks
  fsm_master.png     master FSM state diagram
  fsm_slave.png      slave FSM state diagram

The figures are drawn from the port lists and state encodings in rtl/.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle, Circle

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "architecture"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#12314f"
TEAL = "#0f766e"
LIGHT = "#eef6f8"
GREY = "#5b6b7a"
AMBER = "#b45309"
RED = "#9f1239"


def box(ax, x, y, w, h, title, subtitle=None, fc=LIGHT, ec=NAVY, fs=11, subfs=8.5, lw=1.6):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                                linewidth=lw, edgecolor=ec, facecolor=fc, zorder=2))
    ax.text(x + w / 2, y + h - 0.055, title, ha="center", va="top",
            fontsize=fs, fontweight="bold", color=NAVY, zorder=3)
    if subtitle:
        ax.text(x + w / 2, y + h / 2 - 0.03, subtitle, ha="center", va="center",
                fontsize=subfs, color=GREY, linespacing=1.5, zorder=3)


def arrow(ax, p, q, color=NAVY, lw=1.4, style="-|>", ls="-", rad=0.0, z=4):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle=style, mutation_scale=12,
                                 linewidth=lw, color=color, linestyle=ls,
                                 connectionstyle=f"arc3,rad={rad}", zorder=z))


def label(ax, x, y, text, color=NAVY, fs=8.2, ha="center", va="center", bg=None, rot=0):
    ax.text(x, y, text, fontsize=fs, color=color, ha=ha, va=va, rotation=rot,
            zorder=6, bbox=dict(boxstyle="round,pad=0.18", fc=bg or "white",
                                ec="none", alpha=0.92) if bg else None)


def architecture():
    fig, ax = plt.subplots(figsize=(16, 9), dpi=170)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.5, 0.975, "I2C-Based Game Controller Interface in SoC - RTL Architecture",
            ha="center", va="top", fontsize=17, fontweight="bold", color=NAVY)
    ax.text(0.5, 0.936, "soc_top  |  rtl/i2c_master_apb.v  +  rtl/i2c_game_controller_slave.v",
            ha="center", va="top", fontsize=9.5, color=GREY, family="monospace")

    # dashed SoC boundary
    ax.add_patch(FancyBboxPatch((0.030, 0.335), 0.940, 0.555,
                                boxstyle="round,pad=0.008,rounding_size=0.015",
                                linewidth=1.8, edgecolor=TEAL, facecolor="#fbfdfe",
                                linestyle=(0, (6, 4)), zorder=1))
    ax.text(0.045, 0.862, "soc_top", fontsize=9.5, color=TEAL, fontweight="bold")

    # host
    box(ax, 0.050, 0.455, 0.140, 0.370, "SoC host / APB", "", fs=10.5)
    ax.text(0.120, 0.670, "apb_start\napb_slave_addr[6:0]\nclk, reset",
            ha="center", va="center", fontsize=8.0, color=GREY, linespacing=1.6)

    # master
    box(ax, 0.255, 0.420, 0.265, 0.420, "i2c_master_apb", "", fs=12)
    ax.text(0.3875, 0.735, "single-byte read engine", ha="center", va="center",
            fontsize=8.3, color=TEAL, style="italic")
    ax.text(0.3875, 0.565,
            "FSM: IDLE / START / ADDR\nADDR_ACK / READ / DATA_ACK\nSTOP / DONE\n\n"
            "bit_cnt[3:0]    shift_reg[7:0]\nSCL phase generator\nopen-drain SDA driver",
            ha="center", va="center", fontsize=8.2, color=GREY, linespacing=1.6)

    # slave
    box(ax, 0.630, 0.460, 0.250, 0.355, "i2c_game_controller_slave", "", fs=10.8)
    ax.text(0.755, 0.700, "SLAVE_ADDR = 7'h42", ha="center", va="center",
            fontsize=8.0, color=AMBER, family="monospace")
    ax.text(0.755, 0.565,
            "START detect + address shift\naddress comparator / ACK\ndata_out[7:0] latch\nMSB-first SDA driver",
            ha="center", va="center", fontsize=8.0, color=GREY, linespacing=1.7)

    # controller
    ax.add_patch(FancyBboxPatch((0.935, 0.530), 0.058, 0.180,
                                boxstyle="round,pad=0.008,rounding_size=0.012",
                                linewidth=1.4, edgecolor=AMBER, facecolor="#fff7ed", zorder=2))
    ax.text(0.964, 0.645, "Game", ha="center", va="center", fontsize=7.8,
            fontweight="bold", color=AMBER, zorder=3)
    ax.text(0.964, 0.612, "controller", ha="center", va="center", fontsize=7.8,
            fontweight="bold", color=AMBER, zorder=3)
    ax.text(0.964, 0.568, "buttons", ha="center", va="center", fontsize=7.0,
            color=GREY, zorder=3)

    # bus
    ax.plot([0.520, 0.630], [0.640, 0.640], color=TEAL, lw=2.4, zorder=2)
    ax.plot([0.520, 0.630], [0.575, 0.575], color=TEAL, lw=2.4, zorder=2)
    label(ax, 0.575, 0.660, "scl", color=TEAL, fs=8.2)
    label(ax, 0.575, 0.595, "sda", color=TEAL, fs=8.2)

    # pull-up
    ax.plot([0.575, 0.575], [0.790, 0.738], color=GREY, lw=1.1, zorder=2)
    ax.add_patch(Rectangle((0.565, 0.705), 0.020, 0.033, fill=False, ec=GREY, lw=1.0, zorder=3))
    ax.plot([0.575, 0.575], [0.705, 0.640], color=GREY, lw=1.1, zorder=2)
    label(ax, 0.560, 0.762, "VDD\npull-up", color=GREY, fs=6.8, ha="right")

    # host -> master inputs
    arrow(ax, (0.190, 0.760), (0.255, 0.760))
    arrow(ax, (0.190, 0.700), (0.255, 0.700))
    arrow(ax, (0.190, 0.585), (0.255, 0.585))
    label(ax, 0.221, 0.779, "apb_start", fs=6.9)
    label(ax, 0.221, 0.719, "apb_slave_addr[6:0]", fs=6.7)
    label(ax, 0.221, 0.604, "clk / reset", fs=6.9)

    # master -> host outputs
    arrow(ax, (0.255, 0.520), (0.190, 0.520), color=TEAL)
    arrow(ax, (0.255, 0.478), (0.190, 0.478), color=TEAL)
    label(ax, 0.221, 0.539, "apb_done", color=TEAL, fs=6.9)
    label(ax, 0.216, 0.459, "apb_data_out[7:0]", color=TEAL, fs=5.8)

    # master -> button_status (leaves soc_top below the slave block)
    ax.plot([0.430, 0.430, 0.975], [0.420, 0.415, 0.415], color=TEAL, lw=1.3, zorder=2)
    arrow(ax, (0.960, 0.415), (0.978, 0.415), color=TEAL, lw=1.3)
    label(ax, 0.700, 0.430, "button_status[7:0]  (= apb_data_out)", color=TEAL, fs=7.4)

    # controller -> slave
    arrow(ax, (0.935, 0.640), (0.880, 0.640), color=AMBER)
    label(ax, 0.906, 0.598, "button_state\n[7:0]", color=AMBER, fs=6.0)

    # clk/reset to slave
    ax.plot([0.120, 0.120, 0.755, 0.755], [0.455, 0.365, 0.365, 0.460],
            color=GREY, lw=1.0, ls=(0, (3, 3)), zorder=2)
    label(ax, 0.430, 0.378, "clk / reset", color=GREY, fs=6.9)

    # notes below the boundary
    ax.text(0.035, 0.295, "Signal flow", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.035, 0.268,
            "1. Host presents a 7-bit address and pulses apb_start.\n"
            "2. Master emits START, shifts {address, R/W=1}, samples ACK.\n"
            "3. Addressed slave returns button_state[7:0], MSB first.\n"
            "4. Master ACKs the byte, emits STOP and pulses apb_done.\n"
            "5. apb_data_out drives button_status[7:0].",
            fontsize=7.9, color=GREY, va="top", linespacing=1.65)

    ax.text(0.530, 0.295, "Implementation notes", fontsize=9.2, fontweight="bold", color=NAVY)
    ax.text(0.530, 0.268,
            "- One SCL bit cell = 8 clk cycles (SCL high for 4).\n"
            "- SDA is open-drain with an external pull-up resistor.\n"
            "- Single-byte read, 7-bit addressing, no clock stretching.\n"
            "- The APB port is a request/complete handshake (apb_start/apb_done),\n"
            "  not a full AMBA APB slave with PSEL/PENABLE/PADDR/PWDATA.",
            fontsize=7.9, color=GREY, va="top", linespacing=1.65)

    fig.savefig(OUT / "architecture.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

def state_box(ax, x, y, name, sub, w=0.150, h=0.105):
    ax.add_patch(FancyBboxPatch((x - w/2, y - h/2), w, h,
                                boxstyle="round,pad=0.008,rounding_size=0.018",
                                facecolor=LIGHT, edgecolor=NAVY, lw=1.6, zorder=3))
    ax.text(x, y + 0.016, name, ha="center", va="center", fontsize=10.5,
            fontweight="bold", color=NAVY, zorder=4)
    ax.text(x, y - 0.024, sub, ha="center", va="center", fontsize=7.4, color=GREY, zorder=4)


def edge(ax, a, b, txt, off=(0, 0), color=NAVY, rad=0.0, ls="-", fs=7.0):
    arrow(ax, a, b, color=color, rad=rad, lw=1.4, ls=ls)
    mx, my = (a[0]+b[0])/2 + off[0], (a[1]+b[1])/2 + off[1]
    label(ax, mx, my, txt, fs=fs, color=color)


def master_fsm():
    fig, ax = plt.subplots(figsize=(14.5, 7.2), dpi=170)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.955, "I2C Master FSM (i2c_master_apb)", ha="center", va="top",
            fontsize=16.5, fontweight="bold", color=NAVY)

    top = 0.690; bot = 0.290
    P = {
        "IDLE":     (0.135, top), "START": (0.365, top), "ADDR": (0.595, top),
        "ADDR_ACK": (0.825, top), "READ": (0.825, bot), "DATA_ACK": (0.595, bot),
        "STOP":     (0.365, bot), "DONE": (0.135, bot),
    }
    state_box(ax, *P["IDLE"], "IDLE", "scl=1, sda=1")
    state_box(ax, *P["START"], "START", "SDA 1->0, SCL=1")
    state_box(ax, *P["ADDR"], "ADDR", "8 bits, MSB first")
    state_box(ax, *P["ADDR_ACK"], "ADDR_ACK", "sample ACK (9th)")
    state_box(ax, *P["READ"], "READ", "8 data bits + sample")
    state_box(ax, *P["DATA_ACK"], "DATA_ACK", "drive ACK")
    state_box(ax, *P["STOP"], "STOP", "SDA 0->1, SCL=1")
    state_box(ax, *P["DONE"], "DONE", "apb_done=1")

    edge(ax, (0.210, top), (0.290, top), "apb_start", off=(0, 0.036))
    edge(ax, (0.440, top), (0.520, top), "address\nloaded", off=(0, 0.050))
    edge(ax, (0.670, top), (0.750, top), "8th bit", off=(0, 0.036))
    edge(ax, (0.825, 0.638), (0.825, 0.343), "ACK=0", off=(0.042, 0))
    edge(ax, (0.750, bot), (0.670, bot), "8th bit", off=(0, 0.036))
    edge(ax, (0.520, bot), (0.440, bot), "data\ncaptured", off=(0, 0.050))
    edge(ax, (0.290, bot), (0.210, bot), "stop done", off=(0, 0.036))
    edge(ax, (0.135, 0.343), (0.135, 0.638), "next apb_start", off=(-0.060, 0),
         color=GREY, ls=(0, (3, 2)))

    # NACK: orthogonal route through the gap between the two rows
    ax.plot([0.760, 0.760, 0.365, 0.365], [0.638, 0.520, 0.520, 0.343],
            color=RED, lw=1.4, ls=(0, (4, 2)), zorder=4)
    arrow(ax, (0.365, 0.520), (0.365, 0.343), color=RED, lw=1.4, ls=(0, (4, 2)))
    label(ax, 0.565, 0.533, "NACK after address (SDA=1)", fs=7.0, color=RED)

    ax.text(0.5, 0.090,
            "Transitions and state codes are taken directly from rtl/i2c_master_apb.v. "
            "A NACK after the address aborts the data phase and still terminates with STOP.",
            ha="center", va="bottom", fontsize=8.2, color=GREY)
    fig.savefig(OUT / "fsm_master.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)


def slave_fsm():
    fig, ax = plt.subplots(figsize=(13.5, 7.0), dpi=170)
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")
    ax.text(0.5, 0.955, "Game Controller Slave FSM (i2c_game_controller_slave)",
            ha="center", va="top", fontsize=16, fontweight="bold", color=NAVY)

    P = {"S_IDLE": (0.140, 0.560), "S_ADDR": (0.405, 0.560),
         "S_ACK": (0.670, 0.560), "S_DATA": (0.670, 0.235)}
    state_box(ax, *P["S_IDLE"], "S_IDLE", "bus released")
    state_box(ax, *P["S_ADDR"], "S_ADDR", "shift 8 bits")
    state_box(ax, *P["S_ACK"],  "S_ACK",  "ACK slot")
    state_box(ax, *P["S_DATA"], "S_DATA", "send 8 bits")

    edge(ax, (0.215, 0.560), (0.330, 0.560), "START", off=(0, 0.036))
    edge(ax, (0.480, 0.560), (0.595, 0.560), "8th bit", off=(0, 0.036))
    edge(ax, (0.670, 0.508), (0.670, 0.288), "address match", off=(0.075, 0))

    # no match: route above the top row
    ax.plot([0.615, 0.615, 0.140, 0.140], [0.613, 0.700, 0.700, 0.613],
            color=RED, lw=1.4, ls=(0, (4, 2)), zorder=4)
    arrow(ax, (0.140, 0.700), (0.140, 0.613), color=RED, lw=1.4, ls=(0, (4, 2)))
    label(ax, 0.380, 0.716, "no address match (NACK)", fs=7.0, color=RED)

    # byte sent: route below the top row
    ax.plot([0.595, 0.595, 0.140, 0.140], [0.235, 0.160, 0.160, 0.508],
            color=GREY, lw=1.4, ls=(0, (3, 2)), zorder=4)
    arrow(ax, (0.140, 0.160), (0.140, 0.508), color=GREY, lw=1.4, ls=(0, (3, 2)))
    label(ax, 0.360, 0.186, "byte complete -> wait for next START", fs=7.0, color=GREY)

    ax.text(0.5, 0.070,
            "Address comparison uses {SLAVE_ADDR, R/W=1} with SLAVE_ADDR = 7'h42. "
            "The slave releases SDA after the byte so the master can ACK and issue STOP.",
            ha="center", va="bottom", fontsize=8.2, color=GREY)
    fig.savefig(OUT / "fsm_slave.png", bbox_inches="tight", facecolor="white")
    plt.close(fig)

if __name__ == "__main__":
    architecture()
    master_fsm()
    slave_fsm()
    print("wrote", OUT)
