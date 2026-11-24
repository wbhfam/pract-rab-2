"""Разбор environment markers PEP 508 без eval и внешних библиотек."""

import os
import platform
import re
import sys

from src.versions import Version, matches_one


TOKEN = re.compile(
    r"\s*(?:(?P<string>'[^']*'|\"[^\"]*\")|"
    r"(?P<operator>===|~=|==|!=|<=|>=|<|>)|"
    r"(?P<word>[A-Za-z_][A-Za-z_0-9]*)|(?P<bracket>[()]))"
)
STRING_OPERATIONS = {
    "==": lambda a, b: a == b, "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b, ">": lambda a, b: a > b,
    "<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
    "in": lambda a, b: a in b, "not in": lambda a, b: a not in b,
}


def environment(extra=""):
    """Сформировать стандартные переменные для текущего интерпретатора."""
    return {
        "python_version": ".".join(platform.python_version_tuple()[:2]),
        "python_full_version": platform.python_version(),
        "os_name": os.name, "sys_platform": sys.platform,
        "platform_release": platform.release(),
        "platform_system": platform.system(),
        "platform_version": platform.version(),
        "platform_machine": platform.machine(),
        "platform_python_implementation": platform.python_implementation(),
        "implementation_name": sys.implementation.name,
        "implementation_version": platform.python_version(),
        "extra": extra,
    }


def tokenize(text):
    """Преобразовать строку маркера в типизированные лексемы."""
    result = []
    position = 0
    text = text.strip()
    while position < len(text):
        match = TOKEN.match(text, position)
        if match is None:
            raise ValueError(f"Некорректный маркер: {text}")
        result.append((match.lastgroup, match.group(match.lastgroup)))
        position = match.end()
    return result


def compare(left, operator, right):
    """Сравнить версии по PEP 440 либо строки по правилам маркеров."""
    if operator not in {"in", "not in"}:
        try:
            Version(left)
            Version(right.rstrip(".*"))
        except ValueError:
            pass
        else:
            return matches_one(Version(left), operator, right)
    operation = STRING_OPERATIONS.get(operator)
    if operation is None:
        raise ValueError(f"Недопустимый оператор строк: {operator}")
    return operation(left, right)


class MarkerParser:
    """Рекурсивный спуск: скобки, сравнения, and, затем or."""

    def __init__(self, text, values):
        """Запомнить токены и значения переменных окружения."""
        self.tokens = tokenize(text)
        self.values = values
        self.position = 0

    def peek(self):
        """Посмотреть следующий токен без продвижения."""
        if self.position == len(self.tokens):
            return None
        return self.tokens[self.position][1]

    def take(self):
        """Прочитать токен, отклоняя незавершённое выражение."""
        if self.peek() is None:
            raise ValueError("Незавершённый маркер")
        token = self.tokens[self.position]
        self.position += 1
        return token

    def operand(self):
        """Прочитать строковый литерал или известную переменную."""
        kind, value = self.take()
        if kind == "string":
            return value[1:-1]
        if kind == "word" and value in self.values:
            return self.values[value]
        raise ValueError(f"Неизвестная переменная маркера: {value}")

    def atom(self):
        """Вычислить выражение в скобках либо сравнение."""
        if self.peek() == "(":
            self.take()
            result = self.disjunction()
            if self.take()[1] != ")":
                raise ValueError("Незакрытая скобка маркера")
            return result
        left = self.operand()
        operator = self.take()[1]
        if operator == "not":
            if self.take()[1] != "in":
                raise ValueError("Ожидается not in")
            operator = "not in"
        return compare(left, operator, self.operand())

    def conjunction(self):
        """Вычислить and, обязательно разбирая обе стороны."""
        result = self.atom()
        while self.peek() == "and":
            self.take()
            right = self.atom()
            result = result and right
        return result

    def disjunction(self):
        """Вычислить or с меньшим приоритетом, чем and."""
        result = self.conjunction()
        while self.peek() == "or":
            self.take()
            right = self.conjunction()
            result = result or right
        return result

    def evaluate(self):
        """Вычислить весь маркер; лишние токены являются ошибкой."""
        result = self.disjunction()
        if self.peek() is not None:
            raise ValueError("Лишние токены в маркере")
        return result


def marker_applies(text, extras=()):
    """Проверить маркер для базовых и запрошенных extras-зависимостей."""
    if not text:
        return True
    return any(
        MarkerParser(text, environment(extra)).evaluate()
        for extra in ("", *sorted(extras))
    )
