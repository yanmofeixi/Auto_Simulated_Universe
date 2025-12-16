import argparse
from typing import List, Optional


def build_parser() -> argparse.ArgumentParser:
    """构建普通模拟宇宙命令行参数解析器."""

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--find", type=int, choices=[0, 1], default=1, help="0 录图,1 跑图"
    )

    # 这些参数不传时使用配置文件中的默认值
    parser.add_argument(
        "--consumable",
        type=int,
        choices=[0, 1],
        default=None,
        help="精英/首领战前是否使用左上角消耗品",
    )

    parser.add_argument(
        "--unlock", action="store_true", help="跳过依赖/环境检查(谨慎使用)"
    )

    return parser


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    """解析命令行参数.

    - argv=None:默认读取 sys.argv
    - argv=list:用于测试或被其他入口调用
    """

    return build_parser().parse_args(argv)
