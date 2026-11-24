"""Построение достижимого графа рекурсивным DFS с сохранением циклов."""

import json
from pathlib import Path
import re

from src.repository import PyPIRepository
from src.requirements import normalize, parse_requirement


class TestRepository:
    """Тестовый JSON: объект вида {\"A\": [\"B\"], \"B\": []}."""

    def __init__(self, filename):
        """Проверить формат и существование всех упомянутых узлов."""
        with Path(filename).open(encoding="utf-8") as source:
            self.graph = json.load(source)
        if not isinstance(self.graph, dict) or not self.graph:
            raise ValueError("Тестовый граф должен быть непустым объектом JSON")
        for name, children in self.graph.items():
            validate_test_node(name, children)
        nodes = set(self.graph)
        references = {child for items in self.graph.values() for child in items}
        if not references <= nodes:
            raise ValueError(
                "В тестовом графе есть ссылки на неизвестные пакеты"
            )

    def dependencies(self, node):
        """Вернуть прямые зависимости тестового пакета."""
        if node not in self.graph:
            raise ValueError(f"Пакет {node} отсутствует в тестовом репозитории")
        return list(dict.fromkeys(self.graph[node]))


def validate_test_node(name, children):
    """Проверить имя пакета и список имён его зависимостей."""
    if not re.fullmatch(r"[A-Z]+", name):
        raise ValueError(
            "Имена тестовых пакетов: только большие латинские буквы"
        )
    if not isinstance(children, list):
        raise ValueError(f"Зависимости {name} должны быть массивом")
    for child in children:
        if not isinstance(child, str) or not re.fullmatch(r"[A-Z]+", child):
            raise ValueError(f"Некорректное имя зависимости {name}")


class PackageRepository:
    """Адаптер PyPI к графу: узел содержит имя, extras и точную версию."""

    def __init__(self, url):
        """Создать HTTP-клиент метаданных."""
        self.repository = PyPIRepository(url)

    def dependencies(self, node):
        """Получить соседей; выбрать совместимую версию для каждого ребра."""
        identity, version = node.rsplit("==", 1)
        package = parse_requirement(identity)
        requirements = self.repository.dependencies(
            package.name, version, package.extras
        )
        result = []
        for requirement in requirements:
            selected = self.repository.select(requirement)
            extras = ",".join(sorted(requirement.extras))
            name = requirement.name + (f"[{extras}]" if extras else "")
            result.append(f"{name}=={selected}")
        return list(dict.fromkeys(result))


def build_graph(root, dependencies):
    """Рекурсивный DFS; каждый узел раскрывается только один раз."""
    graph = {}

    def visit(node):
        """Пометить узел до рекурсии, сохраняя обратное ребро цикла."""
        if node in graph:
            return
        graph[node] = list(dependencies(node))
        for child in graph[node]:
            visit(child)

    visit(root)
    return graph


def analyze(config):
    """Выбрать источник и вернуть корень и его достижимый граф."""
    if config.test_mode:
        source = TestRepository(config.repository)
        root = config.package
    else:
        source = PackageRepository(config.repository)
        root = f"{normalize(config.package)}=={config.version}"
    return root, build_graph(root, source.dependencies)
