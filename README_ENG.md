[简体中文](README.md) | [繁体中文](README_CHT.md) | [English](README_ENG.md)

# Auto_Simulated_Universe

Star Rail - Auto Simulated Universe

This project incorporates a pause-resume feature. You can switch to other tasks and return later to continue the automation process.

Currently supports automation of all worlds within the simulated universe.

---

## Disclaimer

This software is an external tool intended to automate gameplay in the game "Honkai Star Rail." It is designed to interact with the game solely through existing user interfaces and in compliance with relevant laws and regulations. This software package aims to provide simplification and user interaction with the game's features and does not intend to disrupt game balance or provide any unfair advantages. The package will not modify any game files or game code in any way.

This software is open-source and free of charge, intended for educational and collaborative purposes only. The development team holds the final interpretation rights for this project. Any issues arising from the use of this software are unrelated to this project and the development team. If you come across merchants using this software for power-leveling and charging for it, the costs might involve equipment and time, and any issues or consequences arising from this software are unrelated to it.

Please note that according to MiHoYo's [Fair Play Declaration for Honkai Star Rail](https://hsr.hoyoverse.com/en-us/news/111244):

    "The use of plug-ins, accelerators, scripts, or other third-party tools that disrupt the fairness of the game is strictly prohibited."
    "Once discovered, miHoYo (hereinafter referred to as 'we') will take measures such as deducting illegal gains, freezing game accounts, and permanently banning game accounts based on the severity and frequency of violations."

### Usage

Only supports 1920x1080 resolution (windowed or fullscreen), turn off hdr, and text language selection is simplified Chinese.

Default World: For instance, if your current default world in the simulated universe is World 4 but you want to automate World 6, please enter World 6 once to change the default world.

**First-time Setup**

Double-click `install_requirements.bat` to install the required libraries.

Rename `info_example.yml` to `info.yml`.

**Running Automation**

Divergent Universe:

```plaintext
python run_diver.py
```

Simulated Universe:

```plaintext
python run_simul.py
```

Detailed parameters:

```plaintext
python run_simul.py --bonus=<bonus> --debug=<debug> --speed=<speed> --find=<find>
```

`bonus` in [0,1]: Whether to enable immersion bonus.

`speed` in [0,1]: Enable speedrun mode.

`consumable` in [0,1]: Use the top-left consumable before elite & boss fights.

`debug` in [0,1,2]: Enable debug mode.

`find` in [0,1]: 0 for recording, 1 for pathfinding.

The content of `info.yml` is as follows:

```yaml
config:
  # Calibration value
  angle: 1.0
  # Difficulty 1-5 (5 is highest, falls back to 4 if 5 unavailable)
  difficulty: 5
  # Team type: 追击/dot/终结技/击破/盾反/白厄盾丹
  team: 终结技
  # Characters to use techniques before boss, in order
  skill:
    - 黄泉
  timezone: Default
  # Image recognition precision
  accuracy: 1440
  # Portal priority 1-3, 3 is highest
  # Set enable_portal_prior to 1 to customize
  enable_portal_prior: 0
  portal_prior:
    商店: 1
    财富: 1
    战斗: 2
    遭遇: 2
    奖励: 3
    事件: 3

key_mapping:
  # Interact key
  - f
  # Map
  - m
  # Sprint
  - shift
  # Auto battle
  - v
  # Technique
  - e
  # Movement
  - w
  - a
  - s
  - d
  # Character switch
  - "1"
  - "2"
  - "3"
  - "4"
```

Prefer using ranged female characters in the first slot whenever possible. Melee females can also be viable, while other body types (e.g., male characters) may result in stability issues.

Important!!! Once you start running/calibrating, do not move the game window! If you need to move it, please stop the automation first!

**Calibration**

If you're experiencing issues like excessive/inadequate camera rotation leading to getting lost, it might be due to calibration. You can manually calibrate as follows:

Enter the game and teleport your character to Herta's office. Then run:

```plaintext
python align_angle.py
```

Changing your mouse DPI might affect calibration values, in which case, you'll need to recalibrate.

---

### Notification Plugin Instructions (notif.exe)

If you're not using a local multi-user setup, simply double-click

`notif.exe` to enable Windows notifications. You'll receive notifications after each completion.

If you're using a local multi-user setup, run the automation in the sub-user account and `notif.exe` in the main user account. This way, notifications will be sent to the main user.

The counter resets automatically weekly. If you wish to manually modify the count, open `logs/notif.txt` and edit the first line.

The notification plugin displays a tray icon in the bottom-right corner.

---

### Logic Overview

Blessing selection logic is based on OCR and custom priority settings.

Pathfinding module uses a mini-map.

The mini-map only recognizes white edge lines and yellow interaction points.

---

Support for recording maps is available:

Run `python run_simul.py --debug=2 --find=1`.

If a new map is encountered and your character stops, end the automation and put the game in pause mode in the Simulated Universe.

Then, run `python run_simul.py --debug=2 --find=0`.

The script will automatically enter the map. During this process, do not move the mouse or press any keys.

After a few seconds, the character will move backward and then forward. During the forward movement, you can move the mouse to change the camera angle or use WASD on the keyboard.

Move around the map, and when you feel it's sufficient, press F8 or Ctrl+C to terminate the process. This will capture the map data. It will be saved in the `imgs/maps/my_xxxxx` directory (sorted by modification time).

For maps with monsters, it's advisable to use Seele's ultimate ability. Being locked onto a target can affect the mini-map recognition.

A `target.jpg` file will be present in the `imgs/maps/my_xxxxx` directory. You can use the built-in Paint application on Windows to open it and mark points (you can refer to the `target.jpg` file in other map folders).

Indigo: Path point, Yellow: Destination, Green: Interaction point (question mark), Red: Enemy point

After recording, you can exit the game and re-run the automation to test the map. If the test is successful, you've successfully recorded a new map!

---

Feel free to join and provide feedback. QQ Group: 831830526

---

If you like this project, you can buy the author a cup of coffee!

![Donate](https://github.com/CHNZYX/Auto_Simulated_Universe/blob/main/imgs/money.jpg)
