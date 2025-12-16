"""普通模拟宇宙自动化(薄入口).

说明:
- 该文件只负责管理员权限提升(UAC)与启动入口.
- 核心逻辑位于 simul/app.py,便于模块化重构与维护.
"""

import pyuac

from simul.app import main


if __name__ == "__main__":
    if not pyuac.isUserAdmin():
        pyuac.runAsAdmin()
    else:
        main()
