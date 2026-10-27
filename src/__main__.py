"""Минимальное CLI: путь к TOML является единственным аргументом."""

import argparse
import sys

from src.config import load_config
from src.graph import analyze


def execute(config):
    """Этап 3: показать списки смежности достижимого графа."""
    _, graph = analyze(config)
    for node, children in graph.items():
        print(f"{node}: {', '.join(children)}")


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
