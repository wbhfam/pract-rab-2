"""Минимальное CLI: путь к TOML является единственным аргументом."""

import argparse
from dataclasses import asdict
import sys

from src.config import load_config


def execute(config):
    """Этап 1: вывести все настраиваемые параметры как ключ=значение."""
    for key, value in asdict(config).items():
        print(f"{key}={value}")


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
