"""Чтение Requires-Dist из метаданных Python-пакетов."""

from dataclasses import dataclass
import re

from src.config import NAME_PATTERN
from src.markers import marker_applies
from src.versions import split_specifiers


@dataclass(frozen=True)
class Requirement:
    """Имя, ограничения версии, extras и маркер зависимости."""

    name: str
    specifiers: tuple
    extras: frozenset
    marker: str


def normalize(name):
    """Нормализовать имя Python-пакета по PEP 503."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_requirement(text):
    """Разобрать Requires-Dist; URL-зависимость отклонить явно."""
    if not isinstance(text, str):
        raise ValueError("Requires-Dist должен содержать строки")
    body, _, marker = text.partition(";")
    match = re.fullmatch(
        rf"\s*({NAME_PATTERN})(?:\[([^\]]+)\])?\s*(.*?)\s*", body
    )
    if match is None:
        raise ValueError(f"Некорректный Requires-Dist: {text}")
    name, extras, specifiers = match.groups()
    if "@" in specifiers:
        raise ValueError("Прямые URL в Requires-Dist не поддерживаются")
    extras = frozenset(
        normalize(item.strip()) for item in (extras or "").split(",")
        if item.strip()
    )
    return Requirement(
        normalize(name), tuple(split_specifiers(specifiers)), extras,
        marker.strip(),
    )


def active_requirements(metadata, extras=()):
    """Получить прямые зависимости для текущего окружения и extras."""
    info = metadata.get("info")
    if not isinstance(info, dict):
        raise ValueError("Ответ репозитория не содержит info")
    entries = info.get("requires_dist")
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError("info.requires_dist: ожидается массив или null")
    result = []
    for entry in entries:
        requirement = parse_requirement(entry)
        if marker_applies(requirement.marker, extras):
            result.append(requirement)
    return result
