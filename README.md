# Вариант 6. Граф зависимостей Python

CLI на Python 3.11+; используются только модули стандартной библиотеки.

## Настройки

Все настройки берутся только из TOML. Аргумент CLI — путь к файлу.
Все пять ключей обязательны; неизвестные ключи запрещены.

- `package`: имя пакета; в тестовом режиме — большие латинские буквы.
- `repository`: базовый URL API PyPI (`https://pypi.org/pypi`)
  или путь к тестовому файлу относительно TOML.
- `test_mode`: логическое значение TOML `true` или `false`.
- `version`: точная версия пакета (строка).
- `ascii_tree`: логическое значение, включает ASCII-дерево на этапе 5.

## Запуск и тесты

Сборка не требуется. Установка сторонних Python-библиотек не требуется.

```sh
./run.sh examples/requests.toml
python3 -B -m unittest discover -s tests -v
```

Из корня также можно запускать `python3 -B -m src examples/requests.toml`.
Ошибки выводятся в stderr; код возврата — 1, ошибка аргументов CLI — 2.

## Функции

- `config.validate_fields`: проверяет набор ключей и типы.
- `config.validate_repository`: проверяет URL или тестовый путь.
- `config.load_config`: читает TOML и проверяет имя и версию.
- `__main__.execute`: на этапе 1 печатает пять пар ключ=значение.
- `__main__.main`: разбирает путь к TOML и обрабатывает ошибки.

## Этап 1

При запуске печатаются все параметры. Ошибки всех пяти настроек,
отсутствующие/лишние ключи и неверный TOML проверяются тестами.

## Этап 2

Источником служит JSON API PyPI: `<repository>/<package>/<version>/json`.
Метаданные получает `urllib.request`, JSON разбирается `json`.
Менеджеры пакетов и сторонние библиотеки приложение не использует.
Читается `info.requires_dist`, учитываются маркеры окружения и extras.
Корневые extras не запрашиваются, поскольку такой настройки в варианте нет.
Версия корневого пакета всегда берётся из TOML, а не из latest.

### Локальная проверка без интернета

В `examples/pypi` сохранены JSON-снимки метаданных локально установленных
пакетов. Это не копия всего PyPI: для каждого пакета доступна одна версия.
Снимки сформированы из файлов METADATA установленного окружения;
их происхождение не подменяется утверждением о загрузке с публичного PyPI.

Первый терминал:

```sh
python3 -B -m http.server 8765 --bind 127.0.0.1 --directory examples
```

Второй терминал:

```sh
./run.sh examples/local-requests.toml
```

На этапе 2 вывод: `charset-normalizer`, `idna`, `urllib3`, `certifi`.
Для публичного PyPI используется `examples/requests.toml`.

### Модули метаданных

- `versions.Version`: разбор и сравнение PEP 440 версий.
- `versions.make_key`, `local_key`: нормализация частей версии.
- `versions.split_specifiers`: разбор ограничений.
- `versions.prefix_matches`, `matches_one`, `compatible`, `exclusive`,
  `satisfies`: проверка спецификаторов.
- `markers.environment`, `tokenize`, `compare`: окружение, лексер и сравнения.
- `markers.MarkerParser`: рекурсивный разбор маркеров без `eval`;
  методы `peek`, `take`, `operand`, `atom`, `conjunction`, `disjunction`,
  `evaluate` реализуют чтение и вычисление выражения.
- `markers.marker_applies`: отбор зависимостей текущего окружения и extras.
- `requirements.normalize`, `parse_requirement`, `active_requirements`:
  нормализация имени и разбор Requires-Dist.
- `repository.PyPIRepository`: кэшируемые запросы `fetch`, точные зависимости
  `dependencies`, выбор подходящей версии зависимости `select`.
- `repository.read_json`, `usable_files`: HTTP/JSON и отбор релизов.

Прямые URL-зависимости вместо имён из репозитория явно отклоняются.
Получение метаданных не устанавливает и не исполняет пакеты.
