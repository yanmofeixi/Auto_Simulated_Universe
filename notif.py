import os
import ctypes
import time
from PIL import Image
from pystray import Icon, MenuItem as item
import threading
import sys
from winotify import Notification

from utils.common.notif_file import read_notif_file
from utils.common.notif_file import write_notif_file

def notif(title,msg):
    Notification(app_id="椰羊自动化",title=title,msg=msg,icon=os.getcwd() + "\\imgs\\icon.png").show()

def exit_program(icon, item):
    icon.stop()
    os._exit(0)

def maopao(icon=None, item=None):
    cnt, _title, _msg, tm = read_notif_file(file_name="logs/notif.txt")
    if not cnt:
        cnt = "0"
    if not tm:
        tm = str(time.time())

    write_notif_file(
        title="喵",
        msg=f"计数:{cnt}",
        cnt=cnt,
        tm=tm,
        file_name="logs/notif.txt",
    )


def clear(icon=None, item=None):
    write_notif_file(
        title="清零",
        msg="计数:0",
        cnt="0",
        tm=str(time.time()),
        file_name="logs/notif.txt",
    )
            
def notify():
    file_name = 'logs/notif.txt'
    if not os.path.exists(file_name):
        with open(file_name, 'w', encoding="utf-8") as file:
            file.write("0")
    last = os.path.getmtime(file_name)
    while 1:
        time.sleep(0.5)
        if last != os.path.getmtime(file_name):
            with open(file_name,'r', encoding="utf-8",errors='ignore') as fh:
                s=fh.readlines()
            if len(s)>=3:
                notif(s[1].strip('\n'),s[2].strip('\n'))
            last = os.path.getmtime(file_name)

def main():
    # 检测程序是否已经在运行
    mutex = ctypes.windll.kernel32.CreateMutexW(None, False, "YEYANG_MyProgramMutex")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(0, "程序已在运行！", "提示", 0x40)
        return

    # 创建系统托盘图标
    image = Image.open("imgs/icon.png")
    icon = Icon("椰羊自动化", image, "椰羊自动化")
    menu = (
        item('冒泡', maopao),
        item('清零', clear),
        item('退出', exit_program),
    )
    icon.menu = menu
    maopao()

    '''
    try:
        mynd = list_handles(f=lambda n:"notif" in n[-9:])[0]
        win32gui.ShowWindow(mynd, 0)
    except:
        pass
    '''

    t_notify = threading.Thread(target=notify)
    t_notify.start()
    # 显示系统托盘图标
    icon.run()


if __name__ == '__main__':
    main()