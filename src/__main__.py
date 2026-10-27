"""Минимальное CLI: путь к TOML является единственным аргументом."""

import argparse
import sys

from src.config import load_config
from src.graph import analyze
from src.order import loading_order


def execute(config):
    """Этап 4: вывести порядок загрузки зависимостей и корневого пакета."""
    root, graph = analyze(config)
    print("\n".join(loading_order(root, graph)))


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
