"""Запуск программы как процесса и коды завершения."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def invoke(*arguments):
    """Запустить CLI из корня проекта без создания pycache."""
    return subprocess.run(
        [sys.executable, "-B", "-m", "src", *map(str, arguments)],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )


class CliTests(unittest.TestCase):
    """Сквозные проверки без HTTP и внешних библиотек."""

    def test_modes(self):
        """Финальный запуск не печатает настройки или порядок загрузки."""
        result = invoke("examples/cycle.toml")
        self.assertEqual(result.returncode, 0)
        self.assertTrue(result.stdout.startswith("digraph dependencies {"))
        self.assertIn("[cycle]", result.stdout)
        self.assertNotIn("package=", result.stdout)
        self.assertEqual(result.stderr, "")

    def test_ascii_disabled(self):
        """При ascii_tree=false выводится только описание DOT."""
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "graph.json").write_text(json.dumps({"A": []}))
            (path / "config.toml").write_text(
                'package="A"\nrepository="graph.json"\ntest_mode=true\n'
                'version="1"\nascii_tree=false\n'
            )
            result = invoke(path / "config.toml")
            self.assertEqual(result.returncode, 0)
            self.assertEqual(
                result.stdout, 'digraph dependencies {\n  "A";\n}\n'
            )

    def test_cli_errors(self):
        """Ошибки конфигурации и аргументов дают ненулевой код без traceback."""
        self.assertEqual(invoke().returncode, 2)
        result = invoke("missing.toml")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Ошибка:", result.stderr)
        self.assertNotIn("Traceback", result.stderr)
