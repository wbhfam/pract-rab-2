"""Точное текстовое представление узлов, рёбер и ASCII-веток."""

import unittest

from src.visualization import to_ascii, to_dot


class VisualizationTests(unittest.TestCase):
    """Визуализация сохраняет структуру исходного графа."""

    def test_dot_leaf(self):
        """Изолированный пакет присутствует как узел DOT."""
        self.assertEqual(to_dot({"A": []}), 'digraph dependencies {\n  "A";\n}')

    def test_dot_cycle_and_quotes(self):
        """Циклическое ребро сохраняется; кавычки экранируются."""
        text = to_dot({"A": ["B"], "B": ["A"]})
        self.assertIn('"A" -> "B";', text)
        self.assertIn('"B" -> "A";', text)
        self.assertIn('"a\\\"b";', to_dot({'a"b': []}))

    def test_ascii_diamond(self):
        """Общий потомок помечается shared и повторно не раскрывается."""
        graph = {"A": ["B", "C"], "B": ["D"], "D": [], "C": ["D"]}
        expected = "\n".join([
            "A", "|-- B", "|   `-- D", "`-- C", "    `-- D [shared]",
        ])
        self.assertEqual(to_ascii("A", graph), expected)
        self.assertTrue(to_ascii("A", graph).isascii())

    def test_ascii_cycles(self):
        """Петля и цикл выводят метку, но не зацикливаются."""
        self.assertEqual(to_ascii("A", {"A": ["A"]}), "A\n`-- A [cycle]")
        text = to_ascii("A", {"A": ["B"], "B": ["A"]})
        self.assertIn("A [cycle]", text)
        self.assertEqual(to_ascii("A", {"A": []}), "A")
