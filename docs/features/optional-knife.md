# Optional knife — нарезка постов только по флагу

Ветка: `mwithout-cutting`

## Проблема

Раньше нарезка common-файла на `001.md`, `002.md`, … была отдельным шагом (`knife_posts.py` или sync внутри `update_*.py`). Легко было случайно нарезать канал, когда нужен был только единый `*_common.md`.

## Решение

1. **По умолчанию** `parser.py` пишет только common-файл.
2. Нарезка — опционально через `--knife`.
3. Папка нарезанных постов: `<channel>_knifed/` **на том же уровне**, что и common-файл.
4. Channel update-скрипты (`update_liminalwriting.py`, `update_twonovelists.py`) тоже только парсят в common, без sync/knife.

## Поведение

| Команда | Результат |
|---|---|
| `parser.py -c durov -o durov_common.md` | Только `durov_common.md` |
| `parser.py -c durov -o durov_common.md --knife` | `durov_common.md` + `durov_knifed/001.md`… |
| `knife_posts.py durov_common.md --out dir` | По-прежнему можно нарезать отдельно |
| `update_liminalwriting.py` | Только `liminalwriting_common.md` |
| `update_twonovelists.py` | Только `twonovelists_common.md` |

Пример раскладки с `--knife`:

```
channels/
  durov_common.md
  durov_knifed/
    001.md
    002.md
    …
```

## Изменённые файлы

| Файл | Что сделано |
|---|---|
| `parser.py` | Флаг `--knife`; после экспорта вызывает `write_individual_posts` |
| `knife_posts.py` | Вынесена `write_individual_posts()` для переиспользования |
| `README.md` | Описан default common-only и `--knife` |
| `update_liminalwriting.py` | Тонкая обёртка над `fetch_and_export`, без knife/sync |
| `update_twonovelists.py` | То же |

## Пути common-файлов (update-скрипты)

Оба update-скрипта пишут прямо в:

`/Users/blacktrope/Library/CloudStorage/Dropbox/soshnikov-writing/channels/`

- `liminalwriting_common.md`
- `twonovelists_common.md`

## Как пользоваться

```bash
# только common
python parser.py --channel liminalwriting --output liminalwriting_common.md

# common + нарезка
python parser.py --channel liminalwriting --output liminalwriting_common.md --knife

# канальные шорткаты
python3 update_liminalwriting.py
python3 update_twonovelists.py
```

## Как проверить

- Без `--knife` рядом с common **не** появляется `*_knifed/`.
- С `--knife` папка `<username>_knifed/` создаётся рядом с output и содержит `NNN.md`.
- Update-скрипты не трогают `night-posts/` и `channels/<name>/`.
