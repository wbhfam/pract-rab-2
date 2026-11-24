"""Зависимости должны предшествовать пакету; цикл запрещает порядок."""

from pathlib import Path
import unittest

from src.config import load_config
from src.graph import analyze
from src.order import loading_order


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class OrderTests(unittest.TestCase):
    """Проверки postorder рекурсивного DFS."""

    def test_diamond(self):
        """Ромб: D, B, C, A; каждое ребро соблюдает зависимость."""
        root, graph = analyze(load_config(EXAMPLES / "diamond.toml"))
        order = loading_order(root, graph)
        self.assertEqual(order, ["D", "B", "C", "A"])
        for node, children in graph.items():
            for child in children:
                self.assertLess(order.index(child), order.index(node))

    def test_cycles(self):
        """Цикл и петля выдают ошибку с маршрутом, а не ложный порядок."""
        for stem in ("cycle", "self"):
            root, graph = analyze(load_config(EXAMPLES / f"{stem}.toml"))
            with self.subTest(stem=stem), self.assertRaisesRegex(
                ValueError, "Цикл: A ->"
            ):
                loading_order(root, graph)

    def test_isolated(self):
        """Без зависимостей загружается только корень."""
        self.assertEqual(loading_order("A", {"A": []}), ["A"])
