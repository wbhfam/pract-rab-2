"""Сравнение версий Python и проверка ограничений без сторонних библиотек."""

from functools import total_ordering
import re

from src.config import VERSION_PATTERN


PARTS = re.compile(
    r"v?(?:(?P<epoch>[0-9]+)!)?"
    r"(?P<release>[0-9]+(?:\.[0-9]+)*)"
    r"(?:[-_.]?(?P<pre>a|b|rc|alpha|beta|preview|pre|c)"
    r"[-_.]?(?P<pre_num>[0-9]*))?"
    r"(?:(?:-(?P<post_short>[0-9]+))|"
    r"(?:[-_.]?(?P<post>post|rev|r)[-_.]?(?P<post_num>[0-9]*)))?"
    r"(?:[-_.]?(?P<dev>dev)[-_.]?(?P<dev_num>[0-9]*))?"
    r"(?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?", re.I
)
PRE_ORDER = {
    "a": 0, "alpha": 0, "b": 1, "beta": 1,
    "c": 2, "rc": 2, "pre": 2, "preview": 2,
}
INFINITY = float("inf")


@total_ordering
class Version:
    """Нормализованная PEP 440 версия с ключом сравнения."""

    def __init__(self, text):
        """Разобрать release, epoch, pre/post/dev и local-компоненты."""
        match = PARTS.fullmatch(text)
        if match is None:
            raise ValueError(f"Некорректная версия: {text}")
        parts = match.groupdict()
        self.text = text
        self.epoch = int(parts["epoch"] or "0")
        self.release = tuple(map(int, parts["release"].split(".")))
        self.pre = parts["pre"]
        self.dev = parts["dev"]
        self.post = parts["post"] or parts["post_short"]
        self.local = parts["local"]
        self.key = make_key(self, parts)

    def __eq__(self, other):
        """Сравнить нормализованные версии."""
        if not isinstance(other, Version):
            return NotImplemented
        return self.key == other.key

    def __lt__(self, other):
        """Упорядочить нормализованные версии."""
        if not isinstance(other, Version):
            return NotImplemented
        return self.key < other.key

    def public(self):
        """Вернуть версию без local-компонента."""
        return Version(self.text.split("+")[0])


def make_key(version, parts):
    """Создать PEP 440 ключ, включая dev перед prerelease."""
    release = list(version.release)
    while release and not release[-1]:
        release.pop()
    pre = (INFINITY, 0)
    if version.pre:
        pre = (PRE_ORDER[version.pre.lower()], int(parts["pre_num"] or "0"))
    elif version.dev and not version.post:
        pre = (-INFINITY, 0)
    post = int(parts["post_num"] or parts["post_short"] or "0")
    post = post if version.post else -INFINITY
    dev = int(parts["dev_num"] or "0") if version.dev else INFINITY
    local = local_key(version.local)
    return version.epoch, tuple(release), pre, post, dev, local


def local_key(local):
    """Числовые сегменты local следуют после строковых."""
    if not local:
        return ()
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.lower())
        for part in re.split(r"[-_.]", local)
    )


def split_specifiers(text):
    """Разобрать конъюнкцию спецификаторов, включая внешние скобки."""
    text = text.strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    if not text:
        return []
    result = []
    for part in text.split(","):
        match = re.fullmatch(r"\s*(===|~=|==|!=|<=|>=|<|>)\s*(\S+)\s*", part)
        if match is None:
            raise ValueError(f"Некорректное ограничение версии: {text}")
        result.append(match.groups())
    return result


def prefix_matches(version, target):
    """Проверить release-prefix для ==X.* и !=X.*."""
    prefix = Version(target[:-2])
    width = len(prefix.release)
    release = version.release + (0,) * width
    return version.epoch == prefix.epoch and release[:width] == prefix.release


def matches_one(version, operator, target):
    """Проверить один спецификатор версии."""
    if operator == "===":
        return version.text.lower() == target.lower()
    if target.endswith(".*"):
        if operator not in {"==", "!="}:
            raise ValueError("Wildcard допустим только с == или !=")
        same = prefix_matches(version, target)
        return same if operator == "==" else not same
    expected = Version(target)
    actual = version if expected.local else version.public()
    if operator == "~=":
        return compatible(actual, expected)
    if operator in {"<", ">"}:
        return exclusive(actual, expected, operator)
    comparisons = {
        "==": actual == expected, "!=": actual != expected,
        "<=": actual <= expected, ">=": actual >= expected,
    }
    return comparisons[operator]


def compatible(actual, expected):
    """Проверить ~= с сохранением всех release-сегментов кроме последнего."""
    if len(expected.release) < len((0, 0)):
        raise ValueError("Для ~= нужны минимум два компонента версии")
    prefix = expected.text.split("+")[0]
    release = ".".join(map(str, expected.release[:-1]))
    prefix = f"{expected.epoch}!{release}.*"
    return actual >= expected and prefix_matches(actual, prefix)


def exclusive(actual, expected, operator):
    """Исключить pre/post той же release-версии у строгих < и >."""
    same_release = actual.key[:2] == expected.key[:2]
    if operator == "<":
        if same_release and not expected.pre and (actual.pre or actual.dev):
            return False
        return actual < expected
    if same_release and not expected.post and actual.post:
        return False
    return actual > expected


def satisfies(text, specifiers):
    """Проверить все ограничения версии одновременно."""
    version = Version(text)
    return all(matches_one(version, op, value) for op, value in specifiers)
