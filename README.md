# remnawave-xray

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

Три режима: **справочник** (ответить по факту, не по памяти), **генератор** (шаблон → плейсхолдеры → чек-лист согласованности), **диагностика** (от симптома к причине + команды).

## ⚠️ Дисклеймер

Материал **образовательный**. Reality/selfsteal/Hysteria — технологии приватности и обхода интернет-цензуры; применяйте в рамках закона вашей юрисдикции. Конфиги в `examples/` **обезличены** (плейсхолдеры вместо доменов/ключей, generic-пути) — как есть они не запускаются, это шаблоны. Версии и «свежие» поля (например, Hysteria 2) сверяйте с актуальными релизами перед проливом в прод.

## Структура

```
SKILL.md                     роутер: инварианты, карта портов, версии, маршрутизация
reference/
  architecture.md            как складывается selfsteal-нода, порты, потоки, xver/proxy_protocol
  xray-reality.md            Reality/Vision параметры (из кода), post-quantum, анти-пробинг
  caddy-selfsteal.md         Caddyfile, ACME, listener_wrappers, DNS-only домен
  mihomo.md                  клиент: DNS/rules/sniffer/TUN + Remnawave-ключи подписки
  remnawave.md               панель/нода/иерархия, SECRET_KEY (mTLS+JWT), injectHosts, SRR
  transports.md              xhttp/ws/grpc/httpupgrade/mkcp/hysteria, матрица security×network
  protocols.md               vmess/trojan/ss/wireguard/VLESS-Encryption + статус HY2/TUIC/AnyTLS
generators.md                шаблоны + команды ключей + чек-лист согласованности
diagnostics.md               симптом → причина → фикс + диагностические команды
examples/                    обезличенные конфиги-эталоны (Xray/Caddy/mihomo/подписка)
```

## Установка

Скопировать папку `remnawave-xray/` в каталог скиллов Claude Code:

- глобально: `~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`)
- или на проект: `<project>/.claude/skills/`

## Использование

Скилл подхватывается **автоматически** на профильные вопросы (Remnawave, selfsteal, Reality-handshake, xray-config, Caddyfile, mihomo, «нода не подключается»), либо вызывается явно: `/remnawave-xray`.

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
