"""差分宇宙自动化(薄入口).

说明:
- 该文件只负责管理员权限提升(UAC)与启动入口.
- 核心逻辑位于 diver/app.py,便于模块化重构与维护.
"""

import sys

import pyuac

from diver.app import main


if __name__ == "__main__":
    # 如果传入 --elevated 参数，跳过 UAC 检查（已经是管理员）
    if "--elevated" in sys.argv or pyuac.isUserAdmin():
        main()
    else:
        pyuac.runAsAdmin()
