"""Чтение и проверка пяти параметров TOML-конфигурации."""

from dataclasses import dataclass
from pathlib import Path
import re
import tomllib
from urllib.parse import urlsplit


NAME_PATTERN = r"[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?"
VERSION_PATTERN = (
    r"v?(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*"
    r"(?:[-_.]?(?:a|b|c|rc|alpha|beta|pre|preview)[-_.]?[0-9]*)?"
    r"(?:(?:-[0-9]+)|(?:[-_.]?(?:post|rev|r)[-_.]?[0-9]*))?"
    r"(?:[-_.]?dev[-_.]?[0-9]*)?"
    r"(?:\+[a-z0-9]+(?:[-_.][a-z0-9]+)*)?"
)
FIELDS = {
    "package": str,
    "repository": str,
    "test_mode": bool,
    "version": str,
    "ascii_tree": bool,
}


@dataclass(frozen=True)
class Config:
    """Проверенные параметры; путь тестового файла абсолютный."""

    package: str
    repository: str
    test_mode: bool
    version: str
    ascii_tree: bool


def validate_fields(data):
    """Проверить полноту, отсутствие лишних ключей и типы значений."""
    if set(data) != set(FIELDS):
        missing = sorted(set(FIELDS) - set(data))
        extra = sorted(set(data) - set(FIELDS))
        raise ValueError(f"Ключи TOML: отсутствуют {missing}; лишние {extra}")
    for key, kind in FIELDS.items():
        if type(data[key]) is not kind:
            raise ValueError(f"{key}: ожидается {kind.__name__}")
        if kind is str and (not data[key] or data[key] != data[key].strip()):
            raise ValueError(f"{key}: пустая строка или пробелы по краям")


def validate_repository(data, base):
    """Проверить HTTP(S) URL либо существование файла тестового графа."""
    value = data["repository"]
    if data["test_mode"]:
        path = (base / value).resolve()
        if not path.is_file():
            raise ValueError("repository: тестовый файл не найден")
        data["repository"] = str(path)
        return
    validate_http_url(value)


def validate_http_url(value):
    """Отклонить неверную схему, пробелы и недопустимые части URL."""
    if any(character.isspace() for character in value):
        raise ValueError("repository: пробелы в URL запрещены")
    parts = urlsplit(value)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("repository: нужен HTTP(S) URL репозитория")
    if any((parts.query, parts.fragment, parts.username, parts.password)):
        raise ValueError(
            "repository: query, fragment и учётные данные запрещены"
        )
    try:
        parts.port
    except ValueError as error:
        raise ValueError("repository: некорректный порт") from error


def load_config(filename):
    """Прочитать TOML; относительный путь графа считать от его каталога."""
    path = Path(filename)
    with path.open("rb") as source:
        data = tomllib.load(source)
    validate_fields(data)
    pattern = r"[A-Z]+" if data["test_mode"] else NAME_PATTERN
    if not re.fullmatch(pattern, data["package"]):
        raise ValueError("package: некорректное имя пакета")
    if not re.fullmatch(VERSION_PATTERN, data["version"], re.I):
        raise ValueError("version: ожидается точная версия Python-пакета")
    validate_repository(data, path.resolve().parent)
    return Config(**data)
