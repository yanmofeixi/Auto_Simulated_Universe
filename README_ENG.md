[简体中文](README.md) | [繁體中文](README_CHT.md) | [English](README_ENG.md)

# Auto Simulated Universe

Honkai: Star Rail - Simulated Universe & Divergent Universe Full Automation Tool

## ✨ Features

- 🌌 **Divergent Universe**: Fully automated Divergent Universe farming
- 🌠 **Simulated Universe**: Fully automated regular Simulated Universe farming
- 🖥️ **GUI**: Built-in Web GUI configuration panel, no manual config file editing required
- 🎯 **Smart Recognition**: OCR-based text recognition for events, blessings, curios, etc.

## ⚠️ Disclaimer

This software is an external tool designed to automate gameplay in Honkai: Star Rail. It only interacts with the game through the existing user interface and does not modify any game files or game code.

This software is open source and free, intended for learning and educational purposes only. The development team reserves the right of final interpretation of this project. All issues arising from the use of this software are not related to this project or the development team.

According to miHoYo's [Honkai: Star Rail Fair Gaming Declaration](https://sr.mihoyo.com/news/111246?nav=news&type=notice):

> "It is strictly forbidden to use plug-ins, accelerators, scripts, or other third-party tools that undermine the fairness of the game."
> "Once discovered, miHoYo will take measures such as deducting illegal gains, freezing game accounts, and permanently banning game accounts depending on the severity and frequency of violations."

## 📋 System Requirements

- Windows 10/11 (macOS/Linux only partially supported)
- Python 3.12
- Screen resolution: 1920×1080 or higher (windowed or fullscreen)
- Game settings: HDR disabled, text language set to Simplified Chinese
- Game interface must be unobstructed

## 🚀 Quick Start

### 1. Install Dependencies

Install the required dependency libraries directly:

```bash
pip install -r requirements.txt
```

> **Note**: If you encounter permission issues, please try running the terminal as an administrator or add the `--user` parameter after the command.

### 2. Launch GUI Configuration Panel

**Windows Users (Recommended)**

- Double-click `start_gui.vbs` - Hidden window launch, only opens browser
- Double-click `start_gui.bat` - Shows console window (for viewing logs)

**Command Line**

```bash
python gui/server.py
```

Your browser will automatically open `http://localhost:8520`, where you can configure all parameters in the interface.

### 3. Run

**Using GUI (Recommended)**

Click "Launch Divergent Universe" or "Launch Simulated Universe" buttons in the configuration panel.

**Using Command Line**

```bash
# Divergent Universe
python run_diver.py

# Simulated Universe
python run_simul.py
```

**Manual Configuration (Advanced Users)**

If you prefer manual configuration, copy `info_example.yml` to `info.yml`, then edit the configuration file.

## ⚙️ Configuration Guide

### General Settings

| Setting      | Description                                                   |
| ------------ | ------------------------------------------------------------- |
| `angle`      | Calibration value (mouse sensitivity multiplier), default 1.0 |
| `difficulty` | Difficulty 1-5, 5 is the highest                              |
| `timezone`   | Timezone setting, default follows system                      |

### Divergent Universe Settings

| Setting        | Description                                                       |
| -------------- | ----------------------------------------------------------------- |
| `accuracy`     | Image recognition accuracy, default 1440, range 960-1920          |
| `team`         | Team type: chase/dot/ultimate/break/shield counter/white e shield |
| `skill`        | List of characters to use techniques in boss rooms                |
| `portal_prior` | Portal priority (1-6, higher number = higher priority)            |

### Simulated Universe Settings

| Setting          | Description                                      |
| ---------------- | ------------------------------------------------ |
| `fate`           | Current path                                     |
| `secondary_fate` | Secondary paths (fallback)                       |
| `use_consumable` | Whether to use consumables                       |
| `prior`          | Priority lists for curios, events, and blessings |

## 🔧 Calibration

If you encounter issues with camera rotation being too large/small causing navigation problems, calibration is needed:

1. Enter the game and teleport your character to Herta's Office
2. Run the calibration script:

```bash
python align_angle.py
```

3. Wait for the camera rotation/spinning to complete

> Note: Changing mouse DPI may affect calibration values and require recalibration.

## 🔔 Notification Plugin

Run `notif.py` to enable Windows notifications after each completed run:

```bash
python notif.py
```

The count resets automatically each week. To manually modify the count, edit `logs/notif.txt`.

## 📁 Project Structure

```
Auto_Simulated_Universe/
├── start_gui.vbs           # GUI launcher (hidden window)
├── start_gui.bat           # GUI launcher (shows console)
├── gui/                    # Web GUI files
│   ├── server.py           # GUI server
│   ├── index.html
│   ├── styles.css
│   └── main.js
├── run_diver.py            # Divergent Universe entry
├── run_simul.py            # Simulated Universe entry
├── diver/                  # Divergent Universe module
├── simul/                  # Simulated Universe module
├── utils/                  # Common utilities
├── data/                   # Data files
│   ├── defaults.json       # Default configuration
│   ├── characters.json     # Character list
│   └── ocr_defaults.json   # OCR default word list
├── info.yml                # User configuration file
└── info_example.yml        # Configuration example
```
