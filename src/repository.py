"""Получение JSON-метаданных PyPI через urllib стандартной библиотеки."""

import json
import platform
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from src.requirements import active_requirements, normalize
from src.versions import Version, satisfies, split_specifiers


TIMEOUT_SECONDS = 30
HTTP_NOT_FOUND = 404


class PyPIRepository:
    """Клиент базового URL API PyPI; менеджеры пакетов не вызываются."""

    def __init__(self, base_url):
        """Запомнить базовый URL и создать кэш JSON-ответов."""
        self.base_url = base_url.rstrip("/")
        self.cache = {}

    def fetch(self, name, version=None):
        """Загрузить /name[/version]/json и обработать сетевые ошибки."""
        path = quote(normalize(name), safe="")
        if version is not None:
            path += "/" + quote(version, safe="")
        url = f"{self.base_url}/{path}/json"
        if url not in self.cache:
            self.cache[url] = read_json(url)
        return self.cache[url]

    def dependencies(self, name, version, extras=()):
        """Получить прямые зависимости именно заданной версии."""
        metadata = self.fetch(name, version)
        info = metadata.get("info")
        if not isinstance(info, dict):
            raise ValueError("В метаданных отсутствует info")
        if not isinstance(info.get("name"), str):
            raise ValueError("info.name: ожидается строка")
        if not isinstance(info.get("version"), str):
            raise ValueError("info.version: ожидается строка")
        if normalize(info["name"]) != normalize(name):
            raise ValueError("Имя в ответе репозитория не совпадает с запросом")
        if Version(info.get("version", "")) != Version(version):
            raise ValueError("Версия в ответе не совпадает с запросом")
        python_spec = split_specifiers(info.get("requires_python") or "")
        if not satisfies(platform.python_version(), python_spec):
            raise ValueError(f"{name}=={version}: несовместимая версия Python")
        return active_requirements(metadata, extras)

    def select(self, requirement):
        """Выбрать наибольшую неотозванную совместимую версию зависимости."""
        releases = self.fetch(requirement.name).get("releases")
        if not isinstance(releases, dict):
            raise ValueError("В метаданных отсутствует releases")
        candidates = candidate_versions(releases, requirement.specifiers)
        stable = [item for item in candidates if is_stable(item)]
        selected = stable or candidates
        if not selected:
            raise ValueError(f"Нет подходящей версии {requirement.name}")
        return max(selected).text


def read_json(url):
    """Прочитать JSON по HTTP; не запускать код скачиваемых пакетов."""
    request = Request(url, headers={"Accept": "application/json"})
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            data = json.load(response)
    except HTTPError as error:
        if error.code == HTTP_NOT_FOUND:
            raise ValueError(
                "Пакет или версия не найдены в репозитории"
            ) from error
        raise ValueError(f"HTTP-ошибка репозитория: {error.code}") from error
    except (URLError, TimeoutError) as error:
        raise ValueError(f"Репозиторий недоступен: {error}") from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Репозиторий вернул некорректный JSON") from error
    if not isinstance(data, dict):
        raise ValueError("Ответ репозитория должен быть JSON-объектом")
    return data


def usable_files(files):
    """Есть ли неотозванный файл, допускающий текущую версию Python."""
    if not isinstance(files, list):
        raise ValueError("releases: ожидается список файлов")
    for item in files:
        if not isinstance(item, dict):
            raise ValueError("Описание файла релиза должно быть объектом")
        specifiers = split_specifiers(item.get("requires_python") or "")
        if not item.get("yanked") and satisfies(
            platform.python_version(), specifiers
        ):
            return True
    return False


def is_stable(version):
    """Определить, является ли версия стабильной."""
    return not version.pre and not version.dev


def candidate_versions(releases, specifiers):
    """Отобрать версии по ограничениям, Requires-Python и yanked."""
    result = []
    for text, files in releases.items():
        try:
            version = Version(text)
        except ValueError:
            continue
        if satisfies(text, specifiers) and usable_files(files):
            result.append(version)
    return result
