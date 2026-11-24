# Проверенные демонстрации этапов

## Этап 1: параметры и ошибки

```text
package=requests
repository=https://pypi.org/pypi
test_mode=False
version=2.34.2
ascii_tree=True
```

Изменение `package = "bad name"`; код 1:

```text
Ошибка: package: некорректное имя пакета
```

Изменение `repository = "ftp://host"`; код 1:

```text
Ошибка: repository: нужен HTTP(S) URL репозитория
```

Изменение `test_mode = "false"`; код 1:

```text
Ошибка: test_mode: ожидается bool
```

Изменение `version = "latest"`; код 1:

```text
Ошибка: version: ожидается точная версия Python-пакета
```

Изменение `ascii_tree = "true"`; код 1:

```text
Ошибка: ascii_tree: ожидается bool
```

## Этап 2: прямые зависимости

HTTP-репозиторий — локальный снимок requests==2.34.2.

```text
charset-normalizer
idna
urllib3
certifi
```

## Этап 3

`diamond.toml`; код 0:

```text
A: B, C
B: D
D: 
C: D
```

`cycle.toml`; код 0:

```text
A: B
B: C
C: A
```

`self.toml`; код 0:

```text
A: A
```

`isolated.toml`; код 0:

```text
A: 
```

## Этап 4

`diamond.toml`; код 0:

```text
D
B
C
A
```

`cycle.toml`; код 1:

```text
Ошибка: Цикл: A -> B -> C -> A
```

`self.toml`; код 1:

```text
Ошибка: Цикл: A -> A
```

`isolated.toml`; код 0:

```text
A
```
