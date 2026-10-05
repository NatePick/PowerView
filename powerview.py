#!/usr/bin/env python3

import os
import re
import sys
import time
import tty
import termios
import select
import signal
import subprocess
from pathlib import Path
from collections import deque


# ============================================================
# PowerView
# macOS GPU Monitor
# ============================================================

VERSION = "0.3.3"

def setup_permissions():
    """Configure one-time permission for PowerView's GPU helper."""

    helper = (
        Path(__file__).resolve().parent
        / "powerview-helper"
    )

    sudoers_path = "/etc/sudoers.d/powerview"

    sudoers_content = (
        f"%admin ALL=(root) NOPASSWD: {helper}\n"
    )

    print("PowerView Setup")
    print()
    print(
        "PowerView requires administrator permission "
        "to access GPU monitoring."
    )
    print()
    print(
        "Administrator access is required once "
        "to configure PowerView."
    )
    print()

    result = subprocess.run(
        [
            "sudo",
            "tee",
            sudoers_path,
        ],
        input=sudoers_content,
        text=True,
        stdout=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        print()
        print("PowerView setup failed.")
        return 1

    result = subprocess.run(
        [
            "sudo",
            "chmod",
            "440",
            sudoers_path,
        ]
    )

    if result.returncode != 0:
        print()
        print("PowerView setup failed.")
        return 1

    result = subprocess.run(
        [
            "sudo",
            "/usr/sbin/visudo",
            "-c",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        print()
        print("ERROR: sudoers validation failed.")
        print()
        print("Remove the rule with:")
        print(
            "sudo rm /etc/sudoers.d/powerview"
        )
        return 1

    print()
    print("PowerView setup completed successfully.")
    print()
    print("You can now run:")
    print("    powerview")

    return 0

# ============================================================
# ANSI TERMINAL CONTROL
# ============================================================

RESET = "\033[0m"
BOLD = "\033[1m"

CLEAR = "\033[2J"
HOME = "\033[H"

HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

ALT_SCREEN_ON = "\033[?1049h"
ALT_SCREEN_OFF = "\033[?1049l"


def fg(hex_color):
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"\033[38;2;{r};{g};{b}m"


def bg(hex_color):
    hex_color = hex_color.lstrip("#")

    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"\033[48;2;{r};{g};{b}m"


# ============================================================
# THEMES
# ============================================================

THEMES = {
    "Default": {
        "primary": "#5FD7FF",
        "accent": "#AF87FF",
        "graph": "#5FD7FF",
        "text": "#E6E6E6",
        "dim": "#909090",
        "good": "#5FD787",
        "warn": "#FFD75F",
        "bad": "#FF5F5F",
        "background": "#101010",
    },

    "Catppuccin Mocha": {
        "primary": "#CBA6F7",
        "accent": "#89B4FA",
        "graph": "#89DCEB",
        "text": "#CDD6F4",
        "dim": "#7F849C",
        "good": "#A6E3A1",
        "warn": "#F9E2AF",
        "bad": "#F38BA8",
        "background": "#1E1E2E",
    },

    "Catppuccin Macchiato": {
        "primary": "#C6A0F6",
        "accent": "#8AADF4",
        "graph": "#91D7E3",
        "text": "#CAD3F5",
        "dim": "#8087A2",
        "good": "#A6DA95",
        "warn": "#EED49F",
        "bad": "#ED8796",
        "background": "#24273A",
    },

    "Dracula": {
        "primary": "#BD93F9",
        "accent": "#8BE9FD",
        "graph": "#50FA7B",
        "text": "#F8F8F2",
        "dim": "#6272A4",
        "good": "#50FA7B",
        "warn": "#F1FA8C",
        "bad": "#FF5555",
        "background": "#282A36",
    },

    "Nord": {
        "primary": "#88C0D0",
        "accent": "#81A1C1",
        "graph": "#8FBCBB",
        "text": "#ECEFF4",
        "dim": "#7B88A1",
        "good": "#A3BE8C",
        "warn": "#EBCB8B",
        "bad": "#BF616A",
        "background": "#2E3440",
    },

    "Gruvbox Dark": {
        "primary": "#FABD2F",
        "accent": "#83A598",
        "graph": "#B8BB26",
        "text": "#EBDBB2",
        "dim": "#928374",
        "good": "#B8BB26",
        "warn": "#FABD2F",
        "bad": "#FB4934",
        "background": "#282828",
    },

    "Tokyo Night": {
        "primary": "#7AA2F7",
        "accent": "#BB9AF7",
        "graph": "#7DCFFF",
        "text": "#C0CAF5",
        "dim": "#565F89",
        "good": "#9ECE6A",
        "warn": "#E0AF68",
        "bad": "#F7768E",
        "background": "#1A1B26",
    },

    "Monokai": {
        "primary": "#66D9EF",
        "accent": "#AE81FF",
        "graph": "#A6E22E",
        "text": "#F8F8F2",
        "dim": "#75715E",
        "good": "#A6E22E",
        "warn": "#E6DB74",
        "bad": "#F92672",
        "background": "#272822",
    },

    "Solarized Dark": {
        "primary": "#268BD2",
        "accent": "#6C71C4",
        "graph": "#2AA198",
        "text": "#839496",
        "dim": "#586E75",
        "good": "#859900",
        "warn": "#B58900",
        "bad": "#DC322F",
        "background": "#002B36",
    },

    "Solarized Light": {
        "primary": "#268BD2",
        "accent": "#6C71C4",
        "graph": "#2AA198",
        "text": "#586E75",
        "dim": "#93A1A1",
        "good": "#859900",
        "warn": "#B58900",
        "bad": "#DC322F",
        "background": "#FDF6E3",
    },

    "One Dark": {
        "primary": "#61AFEF",
        "accent": "#C678DD",
        "graph": "#56B6C2",
        "text": "#ABB2BF",
        "dim": "#5C6370",
        "good": "#98C379",
        "warn": "#E5C07B",
        "bad": "#E06C75",
        "background": "#282C34",
    },

    "Everforest": {
        "primary": "#7FBBB3",
        "accent": "#D699B6",
        "graph": "#A7C080",
        "text": "#D3C6AA",
        "dim": "#859289",
        "good": "#A7C080",
        "warn": "#DBBC7F",
        "bad": "#E67E80",
        "background": "#2D353B",
    },

    "Rose Pine": {
        "primary": "#C4A7E7",
        "accent": "#EBBCBA",
        "graph": "#9CCFD8",
        "text": "#E0DEF4",
        "dim": "#6E6A86",
        "good": "#9CCFD8",
        "warn": "#F6C177",
        "bad": "#EB6F92",
        "background": "#191724",
    },

    "Kanagawa": {
        "primary": "#7E9CD8",
        "accent": "#957FB8",
        "graph": "#7FB4CA",
        "text": "#DCD7BA",
        "dim": "#727169",
        "good": "#98BB6C",
        "warn": "#E6C384",
        "bad": "#E82424",
        "background": "#1F1F28",
    },

    "Material": {
        "primary": "#82AAFF",
        "accent": "#C792EA",
        "graph": "#89DDFF",
        "text": "#EEFFFF",
        "dim": "#546E7A",
        "good": "#C3E88D",
        "warn": "#FFCB6B",
        "bad": "#F07178",
        "background": "#263238",
    },

    "Synthwave": {
        "primary": "#FF7EDB",
        "accent": "#B893FF",
        "graph": "#36F9F6",
        "text": "#FFFFFF",
        "dim": "#848BBD",
        "good": "#72F1B8",
        "warn": "#FEDE5D",
        "bad": "#FE4450",
        "background": "#241B2F",
    },
}


# ============================================================
# CONFIG LOCATION
# ============================================================

def get_real_home():
    """
    PowerView normally runs under sudo because powermetrics
    requires root. Do not accidentally store configuration
    under /var/root/.config.
    """

    sudo_user = os.environ.get("SUDO_USER")

    if sudo_user:
        try:
            import pwd
            return Path(
                pwd.getpwnam(sudo_user).pw_dir
            )
        except Exception:
            pass

    return Path.home()


CONFIG_DIR = get_real_home() / ".config" / "powerview"
CONFIG_FILE = CONFIG_DIR / "config.toml"


DEFAULT_CONFIG = {
    "theme": "Catppuccin Mocha",
    "background_mode": "terminal",
    "graph_style": "filled",
    "update_rate": 1000,
    "history": 120,
    "show_pstates": True,
    "show_throttling": True,
    "show_slices": True,
}


def load_config():
    config = DEFAULT_CONFIG.copy()

    if not CONFIG_FILE.exists():
        return config

    try:
        import tomllib

        with open(CONFIG_FILE, "rb") as file:
            loaded = tomllib.load(file)

        for key in config:
            if key in loaded:
                config[key] = loaded[key]

    except Exception:
        pass

    if config["theme"] not in THEMES:
        config["theme"] = DEFAULT_CONFIG["theme"]

    if config["background_mode"] not in (
        "terminal",
        "theme",
        "black",
    ):
        config["background_mode"] = "terminal"

    if config["graph_style"] not in (
        "filled",
        "line",
    ):
        config["graph_style"] = "filled"

    return config


def save_config(config):
    CONFIG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    content = (
        f'theme = "{config["theme"]}"\n'
        f'background_mode = "{config["background_mode"]}"\n'
        f'graph_style = "{config["graph_style"]}"\n'
        f'update_rate = {config["update_rate"]}\n'
        f'history = {config["history"]}\n'
        f'show_pstates = {str(config["show_pstates"]).lower()}\n'
        f'show_throttling = {str(config["show_throttling"]).lower()}\n'
        f'show_slices = {str(config["show_slices"]).lower()}\n'
    )

    CONFIG_FILE.write_text(content)


# ============================================================
# POWERVIEW
# ============================================================

class PowerView:

    def __init__(self):
        self.config = load_config()

        self.running = True
        self.menu_open = False
        self.menu_index = 0

        self.old_terminal = None
        self.process = None

        self.gpu_name = "Detecting..."
        self.gpu_busy = 0.0
        self.gpu_freq = 0.0
        self.cstate = 0.0

        self.pstates = {}

        self.slice_1 = 0.0
        self.slice_2 = 0.0

        self.throttle_high = 0.0
        self.throttle_normal = 0.0
        self.throttle_med = 0.0
        self.throttle_low = 0.0

        self.gpu_history = deque(
            maxlen=self.config["history"]
        )

        self.last_render = 0.0
        self.force_clear = True

        self.menu_items = [
            "Theme",
            "Background",
            "Graph Style",
            "Update Rate",
            "History",
            "Show P-States",
            "Show Throttling",
            "Show Slices",
            "Save Settings",
            "Reset Defaults",
        ]

    # ========================================================
    # TERMINAL
    # ========================================================

    def setup_terminal(self):
        self.old_terminal = termios.tcgetattr(
            sys.stdin.fileno()
        )

        tty.setcbreak(
            sys.stdin.fileno()
        )

        sys.stdout.write(
            ALT_SCREEN_ON
            + RESET
            + CLEAR
            + HOME
            + HIDE_CURSOR
        )

        sys.stdout.flush()

    def restore_terminal(self):
        if self.old_terminal is not None:
            try:
                termios.tcsetattr(
                    sys.stdin.fileno(),
                    termios.TCSADRAIN,
                    self.old_terminal,
                )
            except Exception:
                pass

        sys.stdout.write(
            RESET
            + SHOW_CURSOR
            + ALT_SCREEN_OFF
        )

        sys.stdout.flush()

    # ========================================================
    # THEME
    # ========================================================

    @property
    def theme(self):
        return THEMES[
            self.config["theme"]
        ]

    def color(self, name):
        return fg(
            self.theme[name]
        )

    def background(self):
        mode = self.config[
            "background_mode"
        ]

        if mode == "theme":
            return bg(
                self.theme["background"]
            )

        if mode == "black":
            return bg("#000000")

        # Terminal mode intentionally sends NO background
        # color so the terminal emulator owns transparency.
        return ""

    # ========================================================
    # GPU NAME
    # ========================================================

    def friendly_gpu_name(self):
        names = {
            "IntelIG":
                "Intel Iris Graphics 6100",
        }

        return names.get(
            self.gpu_name,
            self.gpu_name,
        )

    # ========================================================
    # POWERMETRICS
    # ========================================================

    def start_powermetrics(self):
        helper = (
            Path(__file__).resolve().parent
            / "powerview-helper"
        )
    
        command = [
            "/usr/bin/sudo",
            "-n",
            str(helper),
            str(self.config["update_rate"]),
        ]
    
        env = os.environ.copy()
        env.pop("TERMINFO", None)
    
        self.process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )
    
        os.set_blocking(
            self.process.stdout.fileno(),
            False,
        )

    def stop_powermetrics(self):
        if self.process is not None:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception:
                pass

            self.process = None

    # ========================================================
    # PARSER
    # ========================================================

    def parse_line(self, line):
        match = re.search(
            r"GPU 0 name (.+)",
            line,
        )

        if match:
            self.gpu_name = match.group(1).strip()

        match = re.search(
            r"GPU 0 C-state residency: ([\d.]+)%",
            line,
        )

        if match:
            self.cstate = float(
                match.group(1)
            )

        if "GPU 0 P-state residency:" in line:
            states = re.findall(
                r"(\d+)MHz:\s*([\d.]+)%",
                line,
            )

            self.pstates = {
                int(freq): float(percent)
                for freq, percent in states
            }

        match = re.search(
            r"average active frequency.*?: "
            r"[\d.]+% \(([\d.]+)Mhz\)",
            line,
        )

        if match:
            self.gpu_freq = float(
                match.group(1)
            )

        match = re.search(
            r"GPU 0 GPU Busy ([\d.]+)%",
            line,
        )

        if match:
            self.gpu_busy = float(
                match.group(1)
            )

            self.gpu_history.append(
                self.gpu_busy
            )

        match = re.search(
            r"GPU 0 1Slice\s+on\s+:\s*([\d.]+)%",
            line,
        )

        if match:
            self.slice_1 = float(
                match.group(1)
            )

        match = re.search(
            r"GPU 0 2Slices\s+on\s+:\s*([\d.]+)%",
            line,
        )

        if match:
            self.slice_2 = float(
                match.group(1)
            )

        match = re.search(
            r"Throttle High Priority\(%\):\s*([\d.]+)",
            line,
        )

        if match:
            self.throttle_high = float(
                match.group(1)
            )

        match = re.search(
            r"Throttle NormalHi Priority\(%\):\s*([\d.]+)",
            line,
        )

        if match:
            self.throttle_normal = float(
                match.group(1)
            )

        match = re.search(
            r"Throttle Med Priority\(%\):\s*([\d.]+)",
            line,
        )

        if match:
            self.throttle_med = float(
                match.group(1)
            )

        match = re.search(
            r"Throttle Low Priority\(%\):\s*([\d.]+)",
            line,
        )

        if match:
            self.throttle_low = float(
                match.group(1)
            )

    # ========================================================
    # TEXT HELPERS
    # ========================================================

    def terminal_size(self):
        size = os.get_terminal_size()

        return (
            size.columns,
            size.lines,
        )

    def visible_length(self, text):
        ansi = re.compile(
            r"\x1b\[[0-9;?]*[ -/]*[@-~]"
        )

        return len(
            ansi.sub("", text)
        )

    def fit(self, text, width):
        length = self.visible_length(text)

        if length < width:
            text += " " * (
                width - length
            )

        return text

    # ========================================================
    # BOXES
    # ========================================================

    def border_top(
        self,
        title,
        width,
    ):
        title_text = f"─ {title} "

        remaining = max(
            1,
            width
            - len(title_text)
            - 2,
        )

        return (
            self.color("primary")
            + "╭"
            + title_text
            + "─" * remaining
            + "╮"
            + RESET
        )

    def border_bottom(self, width):
        return (
            self.color("primary")
            + "╰"
            + "─" * (width - 2)
            + "╯"
            + RESET
        )

    def row(
        self,
        content,
        width,
    ):
        usable = width - 4

        content = self.fit(
            content,
            usable,
        )

        return (
            self.color("primary")
            + "│ "
            + RESET
            + content
            + self.color("primary")
            + " │"
            + RESET
        )

    # ========================================================
    # UTILIZATION BAR
    # ========================================================

    def utilization_bar(self, width):
        bar_width = max(
            10,
            width - 26,
        )

        filled = int(
            bar_width
            * min(
                max(self.gpu_busy, 0),
                100,
            )
            / 100
        )

        empty = bar_width - filled

        if self.gpu_busy >= 90:
            color = self.color("bad")

        elif self.gpu_busy >= 70:
            color = self.color("warn")

        else:
            color = self.color("graph")

        return (
            color
            + "█" * filled
            + self.color("dim")
            + "░" * empty
            + RESET
        )

    # ========================================================
    # INFORMATION PANEL
    # ========================================================

    def render_info(self, width):
        lines = []

        gpu = self.friendly_gpu_name()

        lines.append(
            self.border_top(
                f"PowerView {VERSION} ─ {gpu}",
                width,
            )
        )

        usage = (
            f"{BOLD}GPU{RESET} "
            f"{self.color('accent')}"
            f"{self.gpu_busy:5.1f}%"
            f"{RESET}"
            f"     "
            f"{BOLD}Clock{RESET} "
            f"{self.gpu_freq:6.0f} MHz"
        )

        lines.append(
            self.row(
                usage,
                width,
            )
        )

        lines.append(
            self.row(
                self.utilization_bar(width),
                width,
            )
        )

        if self.gpu_history:
            average = (
                sum(self.gpu_history)
                / len(self.gpu_history)
            )

            maximum = max(
                self.gpu_history
            )

            minimum = min(
                self.gpu_history
            )

        else:
            average = 0.0
            maximum = 0.0
            minimum = 0.0

        stats = (
            f"Current {self.gpu_busy:5.1f}%"
            f"    Avg {average:5.1f}%"
            f"    Peak {maximum:5.1f}%"
            f"    Min {minimum:5.1f}%"
        )

        lines.append(
            self.row(
                stats,
                width,
            )
        )

        extra = (
            f"C-State {self.cstate:5.1f}%"
        )

        if self.config["show_slices"]:
            if self.slice_2 > 0:
                slices = "2/2"

            elif self.slice_1 > 0:
                slices = "1/2"

            else:
                slices = "Idle"

            extra += (
                f"    Slices {slices}"
            )

        if self.config["show_throttling"]:
            throttling = any([
                self.throttle_high > 0,
                self.throttle_normal > 0,
                self.throttle_med > 0,
                self.throttle_low > 0,
            ])

            if throttling:
                status = (
                    self.color("bad")
                    + "YES"
                    + RESET
                )

            else:
                status = (
                    self.color("good")
                    + "NO"
                    + RESET
                )

            extra += (
                f"    Throttling {status}"
            )

        lines.append(
            self.row(
                extra,
                width,
            )
        )

        if self.config["show_throttling"]:
            throttle = (
                f"Throttle: "
                f"High {self.throttle_high:.0f}%  "
                f"Normal {self.throttle_normal:.0f}%  "
                f"Med {self.throttle_med:.0f}%  "
                f"Low {self.throttle_low:.0f}%"
            )

            lines.append(
                self.row(
                    throttle,
                    width,
                )
            )

        if (
            self.config["show_pstates"]
            and self.pstates
        ):
            active = [
                (freq, percent)
                for freq, percent
                in self.pstates.items()
                if percent > 0
            ]

            active.sort(
                key=lambda item: item[1],
                reverse=True,
            )

            active = active[:4]

            pstate_text = (
                "P-States: "
                + " | ".join(
                    f"{freq}MHz {percent:.1f}%"
                    for freq, percent
                    in active
                )
            )

            lines.append(
                self.row(
                    pstate_text,
                    width,
                )
            )

        lines.append(
            self.border_bottom(width)
        )

        return lines

    # ========================================================
    # GRAPH
    # ========================================================

    def render_graph(
        self,
        width,
        available_height,
    ):
        lines = []

        lines.append(
            self.border_top(
                "GPU USAGE HISTORY",
                width,
            )
        )

        graph_width = max(
            10,
            width - 10,
        )

        graph_height = max(
            5,
            min(
                available_height - 4,
                18,
            ),
        )

        history = list(
            self.gpu_history
        )[-graph_width:]

        values = (
            [None]
            * (
                graph_width
                - len(history)
            )
            + history
        )

        for row_index in range(
            graph_height
        ):
            top = (
                100
                - (
                    row_index
                    * 100
                    / graph_height
                )
            )

            bottom = (
                100
                - (
                    (row_index + 1)
                    * 100
                    / graph_height
                )
            )

            midpoint = (
                top + bottom
            ) / 2

            tolerance = (
                50 / graph_height
            )

            if row_index == 0:
                label = "100%"

            elif abs(
                midpoint - 75
            ) < tolerance:
                label = " 75%"

            elif abs(
                midpoint - 50
            ) < tolerance:
                label = " 50%"

            elif abs(
                midpoint - 25
            ) < tolerance:
                label = " 25%"

            else:
                label = "    "

            graph_line = ""

            for value in values:
                if value is None:
                    graph_line += " "
                    continue

                if value >= top:
                    if (
                        self.config["graph_style"]
                        == "line"
                    ):
                        graph_line += "│"

                    else:
                        graph_line += "█"

                    continue

                if value > bottom:
                    if (
                        self.config["graph_style"]
                        == "line"
                    ):
                        graph_line += "●"

                    else:
                        fraction = (
                            value - bottom
                        ) / (
                            top - bottom
                        )

                        blocks = "▁▂▃▄▅▆▇"

                        index = int(
                            fraction
                            * len(blocks)
                        )

                        index = max(
                            0,
                            min(
                                index,
                                len(blocks) - 1,
                            ),
                        )

                        graph_line += (
                            blocks[index]
                        )

                else:
                    graph_line += " "

            content = (
                self.color("dim")
                + label
                + "│"
                + RESET
                + self.color("graph")
                + graph_line
                + RESET
            )

            lines.append(
                self.row(
                    content,
                    width,
                )
            )

        axis = (
            self.color("dim")
            + "  0%└"
            + "─" * graph_width
            + RESET
        )

        lines.append(
            self.row(
                axis,
                width,
            )
        )

        seconds = int(
            len(history)
            * self.config["update_rate"]
            / 1000
        )

        left_label = f"-{seconds}s"

        spacing = max(
            1,
            graph_width
            - len(left_label)
            - 3,
        )

        timeline = (
            left_label
            + " " * spacing
            + "NOW"
        )

        lines.append(
            self.row(
                "     " + timeline,
                width,
            )
        )

        lines.append(
            self.border_bottom(width)
        )

        return lines

    # ========================================================
    # FOOTER
    # ========================================================

    def render_footer(self, width):
        controls = (
            f"{self.color('accent')}Q{RESET} Quit"
            f"    "
            f"{self.color('accent')}R{RESET} Reset"
            f"    "
            f"{self.color('accent')}M{RESET} Menu"
            f"    "
            f"{self.color('accent')}T{RESET} Theme"
        )

        return self.fit(
            controls,
            width,
        )

    # ========================================================
    # MENU
    # ========================================================

    def menu_value(self, item):
        if item == "Theme":
            return self.config["theme"]

        if item == "Background":
            return self.config[
                "background_mode"
            ].title()

        if item == "Graph Style":
            return self.config[
                "graph_style"
            ].title()

        if item == "Update Rate":
            return (
                f"{self.config['update_rate']} ms"
            )

        if item == "History":
            return (
                f"{self.config['history']} sec"
            )

        if item == "Show P-States":
            return (
                "Yes"
                if self.config["show_pstates"]
                else "No"
            )

        if item == "Show Throttling":
            return (
                "Yes"
                if self.config["show_throttling"]
                else "No"
            )

        if item == "Show Slices":
            return (
                "Yes"
                if self.config["show_slices"]
                else "No"
            )

        return ""

    def render_menu(
        self,
        width,
        height,
    ):
        menu_width = min(
            68,
            max(
                50,
                width - 4,
            ),
        )

        lines = []

        lines.append(
            self.border_top(
                "PowerView Options",
                menu_width,
            )
        )

        lines.append(
            self.row(
                f"{BOLD}APPEARANCE{RESET}",
                menu_width,
            )
        )

        for index, item in enumerate(
            self.menu_items
        ):
            if item == "Update Rate":
                lines.append(
                    self.row(
                        "",
                        menu_width,
                    )
                )

                lines.append(
                    self.row(
                        f"{BOLD}MONITORING{RESET}",
                        menu_width,
                    )
                )

            if item == "Save Settings":
                lines.append(
                    self.row(
                        "",
                        menu_width,
                    )
                )

                lines.append(
                    self.row(
                        f"{BOLD}GENERAL{RESET}",
                        menu_width,
                    )
                )

            selected = (
                index == self.menu_index
            )

            if selected:
                pointer = (
                    self.color("accent")
                    + "▶"
                    + RESET
                )

            else:
                pointer = " "

            value = self.menu_value(
                item
            )

            if value:
                content = (
                    f"{pointer} "
                    f"{item:<20}"
                    f"[ {value} ]"
                )

            else:
                content = (
                    f"{pointer} {item}"
                )

            lines.append(
                self.row(
                    content,
                    menu_width,
                )
            )

        lines.append(
            self.row(
                "",
                menu_width,
            )
        )

        lines.append(
            self.row(
                "↑↓ Select   ←→ Change   Enter Select   Esc Close",
                menu_width,
            )
        )

        lines.append(
            self.border_bottom(
                menu_width
            )
        )

        left_padding = max(
            0,
            (
                width - menu_width
            ) // 2,
        )

        top_padding = max(
            0,
            (
                height - len(lines)
            ) // 2,
        )

        output = [
            ""
            for _ in range(
                top_padding
            )
        ]

        for line in lines:
            output.append(
                " " * left_padding
                + line
            )

        return output

    # ========================================================
    # SETTINGS
    # ========================================================

    def change_setting(
        self,
        direction,
    ):
        item = self.menu_items[
            self.menu_index
        ]

        if item == "Theme":
            names = list(
                THEMES.keys()
            )

            index = names.index(
                self.config["theme"]
            )

            index = (
                index + direction
            ) % len(names)

            self.config["theme"] = (
                names[index]
            )

        elif item == "Background":
            modes = [
                "terminal",
                "theme",
                "black",
            ]

            index = modes.index(
                self.config[
                    "background_mode"
                ]
            )

            index = (
                index + direction
            ) % len(modes)

            self.config[
                "background_mode"
            ] = modes[index]

            self.force_clear = True

        elif item == "Graph Style":
            styles = [
                "filled",
                "line",
            ]

            index = styles.index(
                self.config[
                    "graph_style"
                ]
            )

            index = (
                index + direction
            ) % len(styles)

            self.config[
                "graph_style"
            ] = styles[index]

        elif item == "Update Rate":
            rates = [
                250,
                500,
                1000,
                2000,
            ]

            current = self.config[
                "update_rate"
            ]

            if current not in rates:
                current = 1000

            index = rates.index(
                current
            )

            index = (
                index + direction
            ) % len(rates)

            self.config[
                "update_rate"
            ] = rates[index]

            self.restart_powermetrics()

        elif item == "History":
            options = [
                30,
                60,
                120,
                300,
            ]

            current = self.config[
                "history"
            ]

            if current not in options:
                current = 120

            index = options.index(
                current
            )

            index = (
                index + direction
            ) % len(options)

            new_history = options[index]

            old_history = list(
                self.gpu_history
            )

            self.config[
                "history"
            ] = new_history

            self.gpu_history = deque(
                old_history[-new_history:],
                maxlen=new_history,
            )

        elif item == "Show P-States":
            self.config[
                "show_pstates"
            ] = not self.config[
                "show_pstates"
            ]

        elif item == "Show Throttling":
            self.config[
                "show_throttling"
            ] = not self.config[
                "show_throttling"
            ]

        elif item == "Show Slices":
            self.config[
                "show_slices"
            ] = not self.config[
                "show_slices"
            ]

    def activate_menu_item(self):
        item = self.menu_items[
            self.menu_index
        ]

        if item == "Save Settings":
            save_config(
                self.config
            )

        elif item == "Reset Defaults":
            self.config = (
                DEFAULT_CONFIG.copy()
            )

            self.gpu_history = deque(
                maxlen=self.config[
                    "history"
                ]
            )

            self.restart_powermetrics()
            self.force_clear = True

        else:
            self.change_setting(1)

    def cycle_theme(self):
        names = list(
            THEMES.keys()
        )

        index = names.index(
            self.config["theme"]
        )

        index = (
            index + 1
        ) % len(names)

        self.config["theme"] = (
            names[index]
        )

    # ========================================================
    # KEYBOARD
    # ========================================================

    def read_key(self):
        """
        Read one logical terminal key.

        Arrow keys are escape sequences. The ESC byte is not
        treated as the Escape key until we know that another
        byte is not following it.
        """

        readable, _, _ = select.select(
            [sys.stdin],
            [],
            [],
            0,
        )

        if not readable:
            return None

        try:
            first = os.read(
                sys.stdin.fileno(),
                1,
            )

        except BlockingIOError:
            return None

        if not first:
            return None

        # Normal key.
        if first != b"\x1b":
            try:
                return first.decode(
                    "utf-8"
                )

            except UnicodeDecodeError:
                return None

        # ESC received.
        #
        # Wait to see if this is the beginning of an
        # escape sequence such as ESC [ A.
        sequence = bytearray(
            first
        )

        readable, _, _ = select.select(
            [sys.stdin],
            [],
            [],
            0.08,
        )

        # Nothing follows -> actual Escape key.
        if not readable:
            return "\x1b"

        while True:
            readable, _, _ = select.select(
                [sys.stdin],
                [],
                [],
                0.02,
            )

            if not readable:
                break

            try:
                chunk = os.read(
                    sys.stdin.fileno(),
                    1,
                )

            except BlockingIOError:
                break

            if not chunk:
                break

            sequence.extend(chunk)

            # CSI / SS3 sequences end with a final byte
            # in the range @ through ~.
            #
            # Do not test the '[' byte itself as the final
            # byte. We need at least three bytes before
            # considering the sequence complete.
            if (
                len(sequence) >= 3
                and 0x40
                <= sequence[-1]
                <= 0x7E
            ):
                break

        try:
            return sequence.decode(
                "ascii"
            )

        except UnicodeDecodeError:
            return None

    def handle_key(self, key):
        if key is None:
            return

        # ====================================================
        # MENU MODE
        # ====================================================

        if self.menu_open:

            # ESC closes menu.
            if key == "\x1b":
                self.menu_open = False
                self.force_clear = True
                self.last_render = 0
                return

            # Up
            if key in (
                "\x1b[A",
                "\x1bOA",
            ):
                self.menu_index = (
                    self.menu_index - 1
                ) % len(
                    self.menu_items
                )

                self.last_render = 0
                return

            # Down
            if key in (
                "\x1b[B",
                "\x1bOB",
            ):
                self.menu_index = (
                    self.menu_index + 1
                ) % len(
                    self.menu_items
                )

                self.last_render = 0
                return

            # Right
            if key in (
                "\x1b[C",
                "\x1bOC",
            ):
                self.change_setting(1)
                self.last_render = 0
                return

            # Left
            if key in (
                "\x1b[D",
                "\x1bOD",
            ):
                self.change_setting(-1)
                self.last_render = 0
                return

            # Enter
            if key in (
                "\r",
                "\n",
            ):
                self.activate_menu_item()
                self.last_render = 0
                return

            # Ignore all other keys while menu is open.
            return

        # ====================================================
        # MAIN SCREEN
        # ====================================================

        if key in (
            "q",
            "Q",
        ):
            self.running = False
            return

        if key in (
            "r",
            "R",
        ):
            self.gpu_history.clear()
            self.last_render = 0
            return

        if key in (
            "m",
            "M",
        ):
            self.menu_open = True
            self.force_clear = True
            self.last_render = 0
            return

        if key in (
            "t",
            "T",
        ):
            self.cycle_theme()
            self.last_render = 0
            return

    # ========================================================
    # RENDERER
    # ========================================================

    def render(self):
        width, height = (
            self.terminal_size()
        )

        # Tiny terminals can't display the interface safely.
        if width < 50 or height < 12:
            output = (
                RESET
                + CLEAR
                + HOME
                + self.background()
                + "PowerView requires a terminal at least "
                + "50 columns wide and 12 rows tall."
            )

            sys.stdout.write(output)
            sys.stdout.flush()
            return

        if self.force_clear:
            output = (
                RESET
                + CLEAR
                + HOME
                + self.background()
            )

            self.force_clear = False

        else:
            output = (
                RESET
                + HOME
                + self.background()
            )

        if self.menu_open:
            lines = self.render_menu(
                width,
                height,
            )

        else:
            info = self.render_info(
                width
            )

            graph_space = max(
                8,
                height
                - len(info)
                - 2,
            )

            graph = self.render_graph(
                width,
                graph_space,
            )

            lines = (
                info
                + graph
                + [
                    self.render_footer(
                        width
                    )
                ]
            )

        rendered_lines = []

        for index in range(height):
            if index < len(lines):
                line = lines[index]

            else:
                line = ""

            rendered_lines.append(
                self.fit(
                    line,
                    width,
                )
            )

        output += "\n".join(
            rendered_lines
        )

        output += RESET

        sys.stdout.write(output)
        sys.stdout.flush()

    # ========================================================
    # MAIN LOOP
    # ========================================================

    def run(self):
        self.setup_terminal()

        try:
            self.start_powermetrics()

            while self.running:

                # Read currently available powermetrics output.
                if self.process is not None:
                    try:
                        while True:
                            line = (
                                self.process
                                .stdout
                                .readline()
                            )

                            if not line:
                                break

                            self.parse_line(
                                line
                            )

                    except (
                        BlockingIOError,
                        TypeError,
                    ):
                        pass

                    except Exception:
                        pass

                # Read one keyboard event.
                key = self.read_key()

                if key is not None:
                    self.handle_key(key)

                # Refresh screen.
                now = time.monotonic()

                if (
                    now - self.last_render
                    >= 0.05
                ):
                    self.render()
                    self.last_render = now

                time.sleep(0.01)

        finally:
            self.stop_powermetrics()

            try:
                save_config(
                    self.config
                )

            except Exception:
                pass

            self.restore_terminal()

# ============================================================
# START
# ============================================================

if __name__ == "__main__":
    if "--setup" in sys.argv:
        sys.exit(
            setup_permissions()
        )

    app = PowerView()

    def shutdown(
        signum,
        frame,
    ):
        app.running = False

    signal.signal(
        signal.SIGINT,
        shutdown,
    )

    app.run()
