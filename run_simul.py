"""普通模拟宇宙自动化(薄入口).

说明:
- 该文件只负责管理员权限提升(UAC)与启动入口.
- 核心逻辑位于 simul/app.py,便于模块化重构与维护.
"""

import sys

if __name__ == "__main__":
    # 如果传入 --elevated 参数,直接运行(已从 GUI 以管理员身份启动)
    if "--elevated" in sys.argv:
        from simul.app import main
        main()
    else:
        # 需要检查管理员权限
        import pyuac
        if pyuac.isUserAdmin():
            from simul.app import main
            main()
        else:
            pyuac.runAsAdmin()
