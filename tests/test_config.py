"""Проверки всех пяти параметров и ошибок чтения TOML."""

from dataclasses import asdict
from pathlib import Path
import tempfile
import unittest

from src.config import load_config


class ConfigTests(unittest.TestCase):
    """Проверка конфигурации без обращения к сети."""

    def setUp(self):
        """Создать временную TOML-конфигурацию."""
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "config.toml"
        self.values = {
            "package": '"requests"',
            "repository": '"https://pypi.org/pypi"',
            "test_mode": "false",
            "version": '"2.34.2"',
            "ascii_tree": "true",
        }

    def load(self, values=None):
        """Записать значения и загрузить проверяемый файл."""
        values = self.values if values is None else values
        text = "\n".join(f"{key} = {value}" for key, value in values.items())
        self.path.write_text(text, encoding="utf-8")
        return load_config(self.path)

    def test_valid(self):
        """Все пять параметров сохраняются."""
        self.assertEqual(set(asdict(self.load())), set(self.values))

    def test_invalid_each_parameter(self):
        """Для каждого параметра отклонить неправильные типы и значения."""
        cases = {
            "package": ['""', '"bad name"', "3"],
            "repository": ['""', '"ftp://host"', "true"],
            "test_mode": ['"false"', "0"],
            "version": ['""', '"latest"', '"1..2"', "1"],
            "ascii_tree": ['"true"', "1"],
        }
        for key, values in cases.items():
            for value in values:
                with self.subTest(key=key, value=value):
                    data = dict(self.values, **{key: value})
                    with self.assertRaises(ValueError):
                        self.load(data)

    def test_missing_and_unknown(self):
        """Все обязательные ключи нужны; лишние ключи запрещены."""
        for key in self.values:
            data = dict(self.values)
            del data[key]
            with self.assertRaises(ValueError):
                self.load(data)
        with self.assertRaises(ValueError):
            self.load(dict(self.values, extra="true"))

    def test_test_repository(self):
        """Путь относительно TOML; имя только из больших латинских букв."""
        graph = self.path.parent / "graph.json"
        graph.write_text('{"A": []}', encoding="utf-8")
        self.values.update(package='"A"', test_mode="true")
        self.values["repository"] = '"graph.json"'
        self.assertEqual(self.load().repository, str(graph))
        self.values["package"] = '"a"'
        with self.assertRaises(ValueError):
            self.load()
        self.values["package"] = '"A"'
        self.values["repository"] = '"missing.json"'
        with self.assertRaises(ValueError):
            self.load()

    def test_bad_file(self):
        """Отсутствующий файл и неверный синтаксис обрабатываются."""
        with self.assertRaises(OSError):
            load_config(self.path)
        self.path.write_text("package = [", encoding="utf-8")
        with self.assertRaises(ValueError):
            load_config(self.path)

    def test_bad_urls(self):
        """Отклонить порт, пробелы, query и учётные данные."""
        for url in ("https://x:bad", "https://x/?a", "https://u:p@x", " x "):
            self.values["repository"] = f'"{url}"'
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.load()
