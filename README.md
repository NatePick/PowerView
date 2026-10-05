# PowerView

PowerView is a terminal-based GPU monitoring utility for macOS.

It was created to provide an `nvtop`-style GPU monitoring experience on macOS
using Apple's built-in `powermetrics` utility.

PowerView displays live GPU information in a customizable terminal interface
with GPU utilization history, clock information, P-states, throttling data,
and more.

## Features

- Live GPU utilization
- GPU clock frequency
- GPU usage history graph
- Current, average, minimum, and peak GPU utilization
- GPU C-State information
- GPU P-State information
- GPU slice activity
- GPU throttling information
- Adjustable update rate
- Adjustable history length
- Multiple graph styles
- Terminal transparency support
- 16 built-in themes
- Interactive settings menu
- Keyboard-driven interface

## Themes

PowerView includes 16 built-in themes:

- Default
- Catppuccin Mocha
- Catppuccin Macchiato
- Dracula
- Nord
- Gruvbox Dark
- Tokyo Night
- Monokai
- Solarized Dark
- Solarized Light
- One Dark
- Everforest
- Rose Pine
- Kanagawa
- Material
- Synthwave

## Requirements

PowerView currently requires:

- macOS
- Python 3.13
- Apple's `powermetrics`
- Administrator privileges for `powermetrics`

PowerView itself runs as the normal user. Elevated privileges are only used
when starting Apple's `powermetrics` utility.

## Installation with MacPorts

PowerView is being prepared for distribution through MacPorts.

Once available:

```bash
sudo port install powerview
