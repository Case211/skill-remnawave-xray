# remnawave-xray

[English](README.en.md) · **Русский**

> **Claude Code / agent skill** для стека **Remnawave + Xray (Reality/Vision) + Caddy selfsteal + mihomo**.
> Справочник по стеку, генератор конфигов и диагностика «симптом → причина → фикс» — из официальной документации и исходников.
>
> *An agent skill for the Remnawave VPN stack: Xray VLESS+Reality+XTLS-Vision, Caddy selfsteal masking, and mihomo (Clash.Meta) clients — reference, config generation, and diagnostics.*

## Что это

Навык (skill) для AI-агента, который держит в одном месте выверенную специфику узкого, быстро меняющегося стека:

- **Remnawave** — панель-оркестратор (Config Profile → Inbound → Host → Squad), нода (RemnaNode = Xray-core), подписки.
- **Xray-core** — VLESS + Reality + XTLS-Vision, транспорты (raw/xhttp/ws/grpc/httpupgrade/mkcp/hysteria), протоколы, Hysteria 2.
- **Caddy** — selfsteal-заглушка (реальный сайт за Reality `target`, ACME, `proxy_protocol`).
- **mihomo (Clash.Meta)** — клиентский конфиг: DNS/fake-ip, rules, sniffer, TUN.

Три режима: **справочник** (ответить по факту, не по памяти), **генератор** (шаблон → плейсхолдеры → чек-лист согласованности + исполняемый валидатор `validate.py`), **диагностика** (от симптома к причине + команды).

## ⚠️ Дисклеймер

Материал **образовательный**. Reality/selfsteal/Hysteria — технологии приватности и обхода интернет-цензуры; применяйте в рамках закона вашей юрисдикции. Конфиги в `examples/` **обезличены** (плейсхолдеры вместо доменов/ключей, generic-пути) — как есть они не запускаются, это шаблоны. Версии и «свежие» поля (например, Hysteria 2) сверяйте с актуальными релизами перед проливом в прод.

## Структура

```
.claude-plugin/
  marketplace.json           манифест маркетплейса
  plugin.json                манифест плагина
skills/remnawave-xray/       ← сам скилл:
  SKILL.md                   роутер: инварианты, карта портов, версии, маршрутизация
  reference/                 architecture · xray-reality · caddy-selfsteal · mihomo · remnawave · transports · protocols · routing
  generators.md              шаблоны + команды ключей + чек-лист согласованности
  validate.py                исполняемая проверка конфига на согласованность (stdlib)
  diagnostics.md             симптом → причина → фикс + диагностические команды
  examples/                  обезличенные конфиги-эталоны (Xray/Caddy/mihomo/подписка)
tools/
  sync-check.py              проверка, что кросс-tool точки входа не разъехались с каноном
```

## Установка

**Claude Code — через marketplace:**

```
/plugin marketplace add Case211/skill-remnawave-xray
/plugin install remnawave-xray@case211
/reload-plugins
```

Или через UI: `/plugin` → таб **Marketplaces** → добавить `Case211/skill-remnawave-xray`, затем в **Discover** установить `remnawave-xray`.

**Вручную** (без marketplace): скопировать папку `skills/remnawave-xray/` в каталог скиллов —
`~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`) или `<project>/.claude/skills/`.

## Использование

После установки скилл подхватывается **автоматически** на профильные вопросы (Remnawave, selfsteal, Reality-handshake, xray-config, Caddyfile, mihomo, «нода не подключается»), либо вызывается явно: `/remnawave-xray`.

## Другие AI-инструменты

Репозиторий **мультиагентный** — точки входа для популярных инструментов (тонкие роутеры на общий контент `skills/remnawave-xray/`, без дублирования):

| Инструмент | Файл |
|---|---|
| Claude Code | `skills/remnawave-xray/SKILL.md` (+ marketplace выше) |
| OpenAI Codex / кросс-стандарт AGENTS.md | `AGENTS.md` |
| Cursor | `.cursor/rules/remnawave-xray.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Gemini CLI | `GEMINI.md` |
| Windsurf / Devin Desktop | `.windsurf/rules/` + `.devin/rules/remnawave-xray.md` |
| Codex / Gemini CLI / Copilot / Zed — lazy skill | `.agents/skills/remnawave-xray/SKILL.md` |

Использование: помести репозиторий (или нужные файлы) в свой проект — инструмент сам подхватит свою точку входа.

Про механику: `AGENTS.md` — кросс-стандарт (его читают Codex, Cursor, Windsurf/Devin, Cline, Roo, Zed, Amp, Continue и др.), статический always-on. **Полноценный skill** с прогрессивным раскрытием по описанию — второй стандарт ([agentskills.io](https://agentskills.io)), его поддерживают Claude Code, Codex, Gemini CLI, GitHub Copilot и Zed (через `.agents/skills/`/`.claude/skills/`). В этом репо skill живёт в `skills/remnawave-xray/` (Claude Code plugin), а `.agents/skills/remnawave-xray/SKILL.md` даёт **ленивую загрузку по описанию** для Codex / Gemini CLI / Copilot / Zed (в контексте только `name`+`description`, тело — при релевантном запросе). Инструменты без skill-поддержки (Cursor / Windsurf / Cline / …) получают роутер (`AGENTS.md`/`GEMINI.md`/rules). Все они ссылаются на один справочник (`reference/`, `generators`, `diagnostics`, `examples/`) — контент не дублируется.

## Версии стека

Актуальны на момент сборки — сверяйте перед деплоем:

| Компонент | Версия |
|---|---|
| Remnawave panel/node | 2.8.0 |
| Xray-core | v26.6.27 (CalVer) |
| Caddy | 2.11.4 |
| mihomo (Clash.Meta) | 1.19.27 |

## Источники

Собрано из официальной документации и исходников, не из блогов:

- Xray-core — [xtls.github.io](https://xtls.github.io/), [github.com/XTLS/Xray-core](https://github.com/XTLS/Xray-core) (в т.ч. `infra/conf/*.go`), [llms-full.txt](https://xtls.github.io/llms-full.txt)
- Remnawave — [docs.rw](https://docs.rw/), исходники `remnawave/{panel,node,backend}`
- Caddy — [caddyserver.com/docs](https://caddyserver.com/docs/)
- mihomo — [wiki.metacubex.one](https://wiki.metacubex.one/)
- selfsteal-практика — community-скрипты (DigneZzZ и др.)

## Лицензия

[AGPL-3.0](./LICENSE).

## Вклад

PR/issue приветствуются — особенно уточнения по свежим фичам Xray (Hysteria 2, VLESS Encryption) и версиям стека.

Перед PR: `python tools/sync-check.py` — проверяет, что тонкие точки входа (`AGENTS.md`, `GEMINI.md`, `.cursor`/`.windsurf`/`.devin`/`.github`, `.agents/`) ссылаются на канон и повторяют актуальные версии из `skills/remnawave-xray/SKILL.md`. Конфиги гоняются через `python skills/remnawave-xray/validate.py <config.json> [Caddyfile]`.
