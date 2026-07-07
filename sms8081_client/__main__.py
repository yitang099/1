import argparse
import sys

from sms8081_client.cli import run_cli


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="8081 查号测验客户端")
    parser.add_argument("--cli", action="store_true", help="命令行模式")
    args = parser.parse_args(argv)
    if args.cli:
        return run_cli()
    from sms8081_client.app import main as run_gui

    return run_gui(argv)


if __name__ == "__main__":
    raise SystemExit(main())
