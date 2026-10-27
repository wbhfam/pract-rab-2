"""Проверки метаданных, ограничений версий и environment markers."""

import io
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from src.markers import MarkerParser, marker_applies
from src.repository import PyPIRepository, read_json, usable_files
from src.requirements import active_requirements, parse_requirement
from src.versions import Version, satisfies, split_specifiers


class VersionTests(unittest.TestCase):
    """Нормализация и базовые операторы PEP 440."""

    def test_order(self):
        """Проверить dev, prerelease, final, post, local и epoch."""
        values = ["1.dev1", "1a1", "1b1", "1rc1", "1", "1+abc", "1.post1"]
        parsed = list(map(Version, values))
        self.assertEqual(sorted(parsed), parsed)
        self.assertEqual(Version("1.0.0"), Version("1"))
        self.assertEqual(Version("1-alpha1"), Version("1a1"))
        self.assertGreater(Version("1!1"), Version("999"))

    def test_specifiers(self):
        """Проверить ограничения и совместимые release-prefix."""
        cases = [
            ("1.5", ">=1,<2,!=1.4", True),
            ("1.4", ">=1,<2,!=1.4", False),
            ("1.4.9", "~=1.4.2", True),
            ("1.5", "~=1.4.2", False),
            ("1.4", "==1.*", True),
            ("1+local", "==1", True),
            ("1rc1", "<1", False),
            ("1.post1", ">1", False),
            ("1", "===1", True),
        ]
        for version, specifiers, expected in cases:
            with self.subTest(version=version, specifiers=specifiers):
                self.assertEqual(
                    satisfies(version, split_specifiers(specifiers)), expected
                )

    def test_invalid(self):
        """Неверные версии и операторы вызывают понятную ошибку."""
        for text in ("latest", "1..2", ""):
            with self.assertRaises(ValueError):
                Version(text)
        with self.assertRaises(ValueError):
            split_specifiers("hello")


class MarkerTests(unittest.TestCase):
    """Маркеры вычисляются без eval и запуска чужого кода."""

    def test_operators(self):
        """and имеет приоритет над or; скобки меняют приоритет."""
        values = {"python_version": "3.13", "os_name": "posix"}
        cases = [
            ('python_version >= "3.9" and os_name == "posix"', True),
            ('os_name == "nt" or python_version < "3.10"', False),
            ('(os_name == "nt" or os_name == "posix")', True),
            ('os_name not in "nt,java"', True),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(
                    MarkerParser(text, values).evaluate(), expected
                )

    def test_extras_and_errors(self):
        """Extras включаются только при запросе; ошибки не скрываются."""
        self.assertFalse(marker_applies('extra == "socks"'))
        self.assertTrue(marker_applies('extra == "socks"', {"socks"}))
        for text in ('unknown == "x"', 'os_name ==', 'os_name == "x" garbage'):
            with self.assertRaises(ValueError):
                marker_applies(text)


class MetadataTests(unittest.TestCase):
    """Получение именно запрошенного релиза и обработка сетевых ошибок."""

    def test_requirements(self):
        """Имя нормализуется; constraints, extras и маркер сохраняются."""
        requirement = parse_requirement('Some_Pkg[x] (>=1,<2); extra == "x"')
        self.assertEqual(requirement.name, "some-pkg")
        self.assertEqual(requirement.extras, {"x"})
        self.assertEqual(requirement.specifiers, ((">=", "1"), ("<", "2")))
        data = {"info": {"requires_dist": ['six>=1', 'x; extra == "dev"']}}
        self.assertEqual(len(active_requirements(data)), 1)
        empty = {"info": {"requires_dist": None}}
        self.assertEqual(active_requirements(empty), [])

    def test_exact_version_url_and_cache(self):
        """URL содержит имя и точную версию; повторный запрос идёт из кэша."""
        payload = {"info": {"name": "A", "version": "1", "requires_dist": []}}
        response = io.BytesIO(json.dumps(payload).encode())
        with patch("src.repository.urlopen", return_value=response) as mocked:
            repo = PyPIRepository("https://example.test/pypi")
            self.assertEqual(repo.dependencies("A", "1"), [])
            self.assertEqual(repo.dependencies("A", "1"), [])
            self.assertEqual(mocked.call_count, 1)
            self.assertEqual(
                mocked.call_args.args[0].full_url,
                "https://example.test/pypi/a/1/json",
            )

    def test_selection(self):
        """Выбор соблюдает ограничения, Requires-Python и yanked."""
        releases = {
            "1.0": [{"yanked": False}],
            "1.5": [{"yanked": False}],
            "1.8": [{"yanked": True}],
            "1.9": [{"requires_python": "<2"}],
            "2.0": [{"yanked": False}],
        }
        repo = PyPIRepository("https://example.test")
        with patch.object(repo, "fetch", return_value={"releases": releases}):
            self.assertEqual(repo.select(parse_requirement("a<2")), "1.5")
        self.assertFalse(usable_files([]))

    def test_errors(self):
        """Неверный JSON, HTTP 404 и недоступная сеть не дают traceback."""
        for error in (
            HTTPError("url", 404, "missing", {}, None), URLError("offline")
        ):
            with patch("src.repository.urlopen", side_effect=error):
                with self.assertRaises(ValueError):
                    read_json("https://example.test")
        with patch("src.repository.urlopen", return_value=io.BytesIO(b"[")):
            with self.assertRaises(ValueError):
                read_json("https://example.test")
