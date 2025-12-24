"""GUI 配置服务器.

提供 REST API 用于:
- 读取/保存配置文件
- 启动差分宇宙/模拟宇宙
- 提供默认配置和角色列表
"""

import json
import os
import subprocess
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

import yaml

# 项目根目录
ROOT_DIR = Path(__file__).parent
GUI_DIR = ROOT_DIR / "gui"
DATA_DIR = ROOT_DIR / "data"
CONFIG_FILE = ROOT_DIR / "info.yml"
DEFAULTS_FILE = DATA_DIR / "defaults.json"
CHARACTERS_FILE = DATA_DIR / "characters.json"

# 服务器端口
SERVER_PORT = 8520


def load_json(path: Path) -> dict:
    """加载 JSON 文件."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def load_yaml(path: Path) -> dict:
    """加载 YAML 文件."""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_yaml(path: Path, data: dict) -> None:
    """保存 YAML 文件."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)


class GUIServerHandler(SimpleHTTPRequestHandler):
    """处理 GUI 请求的 HTTP 服务器."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(GUI_DIR), **kwargs)

    def do_GET(self):
        """处理 GET 请求."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/status":
            self._send_json({"status": "ok"})
        elif path == "/api/config":
            self._handle_get_config()
        elif path == "/api/defaults":
            self._handle_get_defaults()
        elif path == "/api/characters":
            self._handle_get_characters()
        elif path == "/api/constants":
            self._handle_get_constants()
        elif path == "/" or path == "/index.html":
            self.path = "/index.html"
            super().do_GET()
        else:
            super().do_GET()

    def do_POST(self):
        """处理 POST 请求."""
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/config":
            self._handle_save_config()
        elif path == "/api/config/reset":
            self._handle_reset_config()
        elif path == "/api/launch/diver":
            self._handle_launch("diver")
        elif path == "/api/launch/simul":
            self._handle_launch("simul")
        else:
            self._send_error(404, "Not Found")

    def do_OPTIONS(self):
        """处理 CORS 预检请求."""
        self.send_response(200)
        self._add_cors_headers()
        self.end_headers()

    def _add_cors_headers(self):
        """添加 CORS 头."""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, data: dict, status: int = 200):
        """发送 JSON 响应."""
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self._add_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def _send_error(self, status: int, message: str):
        """发送错误响应."""
        self._send_json({"error": message}, status)

    def _read_body(self) -> dict:
        """读取请求体."""
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > 0:
            body = self.rfile.read(content_length).decode("utf-8")
            return json.loads(body)
        return {}

    def _handle_get_config(self):
        """获取当前配置."""
        config = load_yaml(CONFIG_FILE)
        self._send_json(config)

    def _handle_get_defaults(self):
        """获取默认配置."""
        defaults = load_json(DEFAULTS_FILE)
        self._send_json(defaults)

    def _handle_get_characters(self):
        """获取角色列表."""
        characters = load_json(CHARACTERS_FILE)
        self._send_json(characters)

    def _handle_get_constants(self):
        """获取 GUI 所需的常量配置."""
        defaults = load_json(DEFAULTS_FILE)
        characters = load_json(CHARACTERS_FILE)

        constants = {
            "fates": defaults.get("simul_fates", []),
            "portal_types": list(defaults.get("diver_portal_prior", {}).keys()),
            "team_types": defaults.get("team_types", []),
            "timezones": defaults.get("timezones", []),
            "characters": characters.get("all_characters", []),
            "skill_characters": characters.get("skill_characters", []),
            "default_skills": characters.get("skill_characters", []),
            "default_secondary_fates": defaults.get("default_secondary_fates", []),
            "default_angle": defaults.get("default_angle", 1.0),
            "default_difficulty": defaults.get("default_difficulty", 5),
            "default_timezone": defaults.get("default_timezone", "Default"),
            "default_fate": defaults.get("default_fate", "巡猎"),
            "default_order_text": defaults.get("default_order_text", [1, 2, 3, 4]),
            "default_team": defaults.get("default_team", "终结技"),
            "default_accuracy": defaults.get("accuracy", 1440),
            "default_portal_prior": defaults.get("diver_portal_prior", {}),
        }
        self._send_json(constants)

    def _handle_save_config(self):
        """保存配置."""
        try:
            data = self._read_body()
            print(f"[GUI Server] 保存配置到: {CONFIG_FILE}")
            print(f"[GUI Server] 配置内容: {list(data.keys())}")
            save_yaml(CONFIG_FILE, data)
            print(f"[GUI Server] 配置保存成功")
            self._send_json({"success": True})
        except Exception as e:
            print(f"[GUI Server] 保存配置失败: {e}")
            self._send_error(500, str(e))

    def _handle_reset_config(self):
        """重置为默认配置."""
        try:
            defaults = load_json(DEFAULTS_FILE)
            characters = load_json(CHARACTERS_FILE)

            default_config = {
                "config": {
                    "angle": defaults.get("default_angle", 1.0),
                    "difficulty": defaults.get("default_difficulty", 5),
                    "timezone": defaults.get("default_timezone", "Default"),
                    "accuracy": defaults.get("accuracy", 1440),
                    "team": defaults.get("default_team", "终结技"),
                    "skill": characters.get("skill_characters", []),
                    "portal_prior": defaults.get("diver_portal_prior", {}),
                    "fate": defaults.get("default_fate", "巡猎"),
                    "secondary_fate": defaults.get("default_secondary_fates", []),
                    "order_text": defaults.get("default_order_text", [1, 2, 3, 4]),
                    "map_sha": "",
                    "use_consumable": 0,
                },
                "prior": defaults.get("simul_prior", {}),
            }

            save_yaml(CONFIG_FILE, default_config)
            self._send_json({"success": True})
        except Exception as e:
            self._send_error(500, str(e))

    def _handle_launch(self, mode: str):
        """启动程序."""
        try:
            if mode == "diver":
                script = ROOT_DIR / "run_diver.py"
            else:
                script = ROOT_DIR / "run_simul.py"

            if sys.platform == "win32":
                # Windows: 使用 ShellExecuteW 以管理员身份启动
                # 传递 --elevated 参数跳过 pyuac 的二次提升
                import ctypes
                ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",  # 以管理员身份运行
                    sys.executable,
                    f'"{script}" --elevated',
                    str(ROOT_DIR),
                    1  # SW_SHOWNORMAL
                )
            else:
                # macOS/Linux: 后台运行
                subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    cwd=str(ROOT_DIR),
                    start_new_session=True,
                )

            self._send_json({"success": True, "mode": mode})
        except Exception as e:
            self._send_error(500, str(e))

    def log_message(self, format, *args):
        """自定义日志格式."""
        print(f"[GUI Server] {args[0]}")


def main():
    """启动服务器."""
    print(f"=" * 50)
    print(f"Auto Simulated Universe - GUI 服务器")
    print(f"=" * 50)
    print(f"服务器地址: http://localhost:{SERVER_PORT}")
    print(f"配置文件: {CONFIG_FILE}")
    print(f"按 Ctrl+C 停止服务器")
    print(f"=" * 50)

    server = HTTPServer(("localhost", SERVER_PORT), GUIServerHandler)
    
    # 自动打开浏览器
    import webbrowser
    webbrowser.open(f"http://localhost:{SERVER_PORT}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        server.shutdown()


if __name__ == "__main__":
    main()
