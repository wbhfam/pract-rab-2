"""Транзитивность, порядок DFS, циклы и ошибки тестового репозитория."""

import json
from pathlib import Path
import tempfile
import unittest

from src.config import load_config
from src.graph import PackageRepository, TestRepository, analyze, build_graph
from src.requirements import parse_requirement
from unittest.mock import patch


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class GraphTests(unittest.TestCase):
    """DFS должен быть рекурсивным и не терять циклические рёбра."""

    def test_diamond(self):
        """Общий потомок раскрывается однократно, недостижимый Z исключён."""
        source = TestRepository(EXAMPLES / "diamond.json")
        calls = []

        def dependencies(node):
            """Записать порядок обращений к источнику."""
            calls.append(node)
            return source.dependencies(node)

        graph = build_graph("A", dependencies)
        self.assertEqual(calls, ["A", "B", "D", "C"])
        self.assertEqual(graph["C"], ["D"])
        self.assertNotIn("Z", graph)

    def test_cycles_and_isolated(self):
        """Цикл, петля и изолированный узел завершаются без зацикливания."""
        for stem in ("cycle", "self", "isolated"):
            with self.subTest(stem=stem):
                root, graph = analyze(load_config(EXAMPLES / f"{stem}.toml"))
                self.assertEqual(root, "A")
                self.assertIn("A", graph)
        graph = analyze(load_config(EXAMPLES / "cycle.toml"))[1]
        self.assertEqual(graph["C"], ["A"])

    def test_invalid_repository(self):
        """Неверный JSON-граф и неизвестные ссылки отклоняются."""
        cases = [[], {}, {"a": []}, {"A": "B"}, {"A": [3]}, {"A": ["B"]}]
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            for data in cases:
                path.write_text(json.dumps(data), encoding="utf-8")
                with self.subTest(data=data), self.assertRaises(ValueError):
                    TestRepository(path)

    def test_missing_root_and_duplicates(self):
        """Нет корня — ошибка; повторяющиеся рёбра удаляются."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "graph.json"
            path.write_text('{"A": ["B", "B"], "B": []}', encoding="utf-8")
            source = TestRepository(path)
            self.assertEqual(source.dependencies("A"), ["B"])
            with self.assertRaises(ValueError):
                source.dependencies("Z")

    def test_package_adapter(self):
        """Точная версия корня и версия зависимости передаются в API."""
        source = PackageRepository("https://example.test")
        dependency = parse_requirement("child[x]>=2")
        with patch.object(source.repository, "dependencies") as dependencies:
            dependencies.return_value = [dependency]
            with patch.object(source.repository, "select", return_value="2.1"):
                self.assertEqual(
                    source.dependencies("root==1.0"), ["child[x]==2.1"]
                )
            dependencies.assert_called_once_with("root", "1.0", frozenset())
