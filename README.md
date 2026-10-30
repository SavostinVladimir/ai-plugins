# Agent Frameworks — Codex

Выборочная установка и обновление наборов навыков и агентов Codex.
Сейчас доступен **spec-review 1.0.0** с пятью независимыми ревьюерами.

## Установка

Требуется Python 3.11+, внешних зависимостей нет. Проверьте `python3 --version`;
если системный Python старее, используйте `python3.11` или более новый.

```bash
python3 manage.py list
python3 manage.py plan spec-review
python3 manage.py install spec-review
python3 manage.py check
```

Это установка пакета нашим CLI, а не через нативный каталог Plugins.
Менеджер копирует готовые Codex-файлы, не запускает модели и не меняет нативный
config.toml. После загрузки конфигурации клиентом откройте чат и вызовите
`$spec-review` с исходным запросом и спекой. Live-доступ к модели и независимый
контекст проверяются отдельно в Codex; `check` проверяет только файлы.

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
