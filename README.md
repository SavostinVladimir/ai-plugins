# Agent Frameworks — Codex

Выборочная установка и обновление наборов навыков и агентов Codex.
Доступны **spec-review 1.0.0** с пятью ревьюерами спеки и
**code-review 1.1.0** с семью ревьюерами кода.

## Установка

Требуется Python 3.11+, внешних зависимостей нет. Проверьте `python3 --version`;
если системный Python старее, используйте `python3.11` или более новый.

```bash
python3 manage.py list
python3 manage.py plan spec-review
python3 manage.py install spec-review
python3 manage.py plan code-review
python3 manage.py install code-review
python3 manage.py check
```

Это установка пакета нашим CLI, а не через нативный каталог Plugins.
Менеджер копирует готовые Codex-файлы, не запускает модели и не меняет нативный
config.toml. После загрузки конфигурации клиентом откройте чат и вызовите
`$spec-review` с исходным запросом и спекой. Live-доступ к модели и независимый
контекст проверяются отдельно в Codex; `check` проверяет только файлы.

Для ревью кода вызовите `$code-review` и укажите изменения (например, относительно
`main`), спеку и исходный запрос. Семь ролей проверяют конкурентность и целостность
состояния, качество тестов, архитектуру, оверинжиниринг и простоту кода, кодстайл проекта,
только критические уязвимости OWASP и точное соответствие реализации спеке.
Определения находятся в `frameworks/code-review/agents/`, навык — в
`frameworks/code-review/skills/code-review/`.

Каждая роль запускается на `gpt-6-luna` с `high`, с чистым контекстом
(`fork_turns="none"`). Ревьюеры работают параллельно, при ограничении слотов —
волнами. Каждый получает код и только нужные ему входные данные; исходный запрос
и спека целиком передаются роли соответствия. Кодстайл сначала ищется в
`AGENTS.md`/`README.md`. Если нужных правил нет, ревьюер просит главного агента
запустить отдельного субагента для их выявления и записи в `AGENTS.md`, после чего
проверка стиля повторяется. Отсутствующая спека означает неполную проверку
соответствия, остальные роли продолжают работу. Отдельное ревью не разрешает
исправлять реализацию.

При реализации общий проход запускается один раз, когда основной агент написал
первую полную версию кода и считает её готовой к ревью. Последующие замечания
человека и их исправления не запускают всех ревьюеров заново: достаточно целевых
проверок, а при существенном нерешённом вопросе — конкретной затронутой роли.
Новый полный проход нужен по явному запросу пользователя или для новой задачи
реализации. Роль `code-simplicity`, вдохновлённая
[Ponytail](https://github.com/DietrichGebert/ponytail), ищет лишние механизмы,
проверки доказанно невозможных состояний и более простые читаемые решения,
сохраняя необходимую валидацию и обработку ошибок.

## Исходники агентов

```text
frameworks/spec-review/
├── manifest.toml
├── agents/
│   ├── spec-alignment.toml
│   ├── spec-excess.toml
│   ├── spec-gaps.toml
│   ├── spec-grounding.toml
│   └── spec-cuj.toml
├── skills/spec-review/
│   ├── SKILL.md
│   └── agents/openai.yaml
├── instructions.md
└── tests/
```

Модель находится непосредственно в каждом `agents/*.toml`:

```toml
model = "gpt-6-luna"
model_reasoning_effort = "high"
```

Редактируйте эти файлы в репозитории, затем запускайте update. Отдельных профилей
моделей и компиляции общих промптов нет. На установке исходник агента сохраняется
без изменений, если не заданы локальные overrides. Параметр `{{agents_path}}` в
SKILL.md подставляется из фактического каталога установки для корпоративных путей.

## Обновление и удаление

```bash
git pull --ff-only
python3 manage.py status
python3 manage.py update spec-review
python3 manage.py update --installed
python3 manage.py uninstall spec-review --dry-run
python3 manage.py uninstall spec-review
```

Обновление берёт исходники из локального checkout и не выполняет сетевых действий.
`--installed` выбирает только установленные пакеты. Версия пакета — в manifest.toml;
для фиксации версии используйте Git tag/commit. Откат версии — checkout нужного
релиза и update. Plan и --dry-run не пишут файлы, конфликты дают код выхода 2.

## Общая папка настроек Codex

Чтобы посмотреть план установки в конкретную папку, выполните из каталога
этого репозитория:

```bash
python3 manage.py plan spec-review --codex-home /путь/к/codex
```

Замените `/путь/к/codex` на каталог настроек вашего Codex. Команда покажет пути
установки навыка, агентов и глобальных инструкций, а также возможные конфликты.
Она не создаёт папки и не меняет файлы. Для установки замените `plan` на `install`,
сохранив тот же `--codex-home`. Этот флаг задаёт место установки; Codex должен
быть настроен на чтение выбранного каталога.

Для песочницы можно передать только один путь:

```bash
python3 manage.py plan spec-review --codex-home /mounted/codex
python3 manage.py install spec-review --codex-home /mounted/codex
```

Размещение:

```text
/mounted/codex/
├── agents/                         пять агентов
├── skills/spec-review/             навык
├── AGENTS.md                       только управляемый блок, остальной текст сохранён
├── config.toml                     существующий файл; менеджер не пишет его
└── .agent-frameworks/state/default/ registry и резервные копии
```

Если в этой папке есть AGENTS.override.md, правило добавляется в него вместо
AGENTS.md. Используйте тот же --codex-home для update, status, check и uninstall.
С отдельными --agents-path/--skills-path и instance.paths можно явно переопределить
компоненты; эти настройки приоритетнее общего корня. Относительный --codex-home
отсчитывается от cwd. Без флага старые пути и registry не меняются.
Новый общий корень не переносит прежнюю установку автоматически: перед миграцией
проверьте plan, чтобы не получить две копии навыка.

Защита: config.toml неизменен; чужой payload и ручные изменения вызывают конфликт
до записи. --adopt только явно разрешает замену неуправляемого файла пакета с
сохранением оригинала; он не даёт права переписать нативный конфиг или чужие правила.
После ошибки записи выполненные изменения откатываются. Plan ничего не создаёт.
Подробная спецификация: [codex-home.md](docs/codex-home.md).

## Пути и экземпляры

Скопируйте examples/instances.toml в локальный файл вне Git и задайте свои пути:

```bash
python3 manage.py plan spec-review --config /path/to/instances.toml --instance corporate-codex
python3 manage.py install spec-review --config /path/to/instances.toml --instance corporate-codex
python3 manage.py update --installed --config /path/to/instances.toml --instance corporate-codex
```

Можно отдельно указать --agents-path, --skills-path, --instructions-path,
--config-path, --state-path. Приоритет: CLI → экземпляр → CODEX_HOME/defaults.
Относительные пути в TOML отсчитываются от него, флаги — от cwd. --config — файл
нашего менеджера, --config-path — диагностический путь нативного конфига Codex.
Произвольные корпоративные пути нужно подключить и в самом harness.

При желании можно локально переопределить конкретную роль:

```toml
[instances.work]

[instances.work.roles.spec-grounding]
model = "available-model"
effort = "medium"
```

CLI --model/--effort имеет высший приоритет текущей операции; явные настройки
запоминаются для следующих update. Настройки экземпляра перекрывают запомненные,
а --reset-overrides сбрасывает их перед применением текущих. `--effort default`
убирает поле effort. В отсутствие overrides используются поля исходного TOML.

## Сохранность

Обновляются только управляемые файлы и блоки инструкций. Ручные изменения
вызывают конфликт. --adopt позволяет осознанно заменить неуправляемый payload
с сохранением оригинала, но не обходит drift и не заменяет глобальные инструкции.
Есть registry, блокировка операций и recovery journals. Ошибки записи вызывают
откат; сбой питания требует проверки журнала. Uninstall восстанавливает исходные
файлы и сохраняет посторонние правила, backups и state.

Текущие живые настройки Codex автоматически не изменяются. Для уже установленной
ручной версии сначала прочитайте [миграцию](docs/installation.md).

## Разработка

```bash
python3 -m unittest discover -s tests -v
```

Тесты изолированы во временных каталогах и не вызывают модели.

- [Корпоративные окружения](docs/corporate-environments.md)
- [Добавление пакета](docs/adding-frameworks.md)
- [Спецификация](docs/specification.md)
- [Codex subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Codex skills](https://learn.chatgpt.com/docs/build-skills)
