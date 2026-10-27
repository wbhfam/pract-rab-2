"""Минимальное CLI: путь к TOML является единственным аргументом."""

import argparse
import sys

from src.config import load_config
from src.repository import PyPIRepository


def execute(config):
    """Этап 2: вывести прямые зависимости заданной версии пакета."""
    if config.test_mode:
        raise ValueError("Тестовый репозиторий реализуется на этапе 3")
    repository = PyPIRepository(config.repository)
    for dependency in repository.dependencies(config.package, config.version):
        print(dependency.name)


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
