"""Минимальное CLI: путь к TOML является единственным аргументом."""

import argparse
import sys

from src.config import load_config
from src.graph import analyze
from src.visualization import to_ascii, to_dot


def execute(config):
    """Этап 5: вывести DOT и, если указано в TOML, ASCII-дерево."""
    root, graph = analyze(config)
    print(to_dot(graph))
    if config.ascii_tree:
        print()
        print(to_ascii(root, graph))


def main():
    """Прочитать конфигурацию и вернуть код завершения CLI."""
    parser = argparse.ArgumentParser(description="Граф зависимостей Python")
    parser.add_argument("config", help="путь к TOML-конфигурации")
    arguments = parser.parse_args()
    try:
        execute(load_config(arguments.config))
    except (OSError, ValueError, RecursionError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
