"""Сквозные проверки реального HTTP без обращения к внешней сети."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import unittest

from src.config import Config
from src.graph import analyze
from src.order import loading_order
from src.repository import PyPIRepository
from src.visualization import to_ascii, to_dot


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


class QuietHandler(SimpleHTTPRequestHandler):
    """Стандартный сервер со скрытым служебным журналом тестов."""

    def log_message(self, format_string, *args):
        """Не печатать HTTP-запросы в отчёт unittest."""


class HttpTests(unittest.TestCase):
    """Запросы точных версий, транзитивность и сравнение трёх примеров."""

    @classmethod
    def setUpClass(cls):
        """Поднять localhost-сервер на свободном порту."""
        handler = partial(QuietHandler, directory=str(EXAMPLES))
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.thread = Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.url = f"http://127.0.0.1:{cls.server.server_port}/pypi"

    @classmethod
    def tearDownClass(cls):
        """Закрыть сервер и дождаться завершения его потока."""
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_three_packages(self):
        """Проверить ожидаемые рёбра и топологический порядок."""
        cases = [
            ("requests", "2.34.2", {
                "charset-normalizer==3.5.2", "idna==3.20",
                "urllib3==2.8.0", "certifi==2026.10.19",
            }),
            ("python-dateutil", "3.0.0", {"six==1.17.0", "tzdata==2026.5"}),
            ("packaging", "26.3", set()),
        ]
        for name, version, children in cases:
            config = Config(name, self.url, False, version, True)
            with self.subTest(name=name):
                root, graph = analyze(config)
                self.assertEqual(set(graph[root]), children)
                self.assertEqual(set(graph), children | {root})
                self.assertEqual(loading_order(root, graph)[-1], root)
                self.assertIn(root, to_dot(graph))
                self.assertTrue(to_ascii(root, graph).startswith(root))

    def test_missing_release(self):
        """Не подменять отсутствующий релиз последним доступным."""
        repository = PyPIRepository(self.url)
        with self.assertRaisesRegex(ValueError, "не найдены"):
            repository.dependencies("requests", "0.0.0")
