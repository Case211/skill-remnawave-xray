---
name: remnawave-xray
description: >-
  Use when working with a Remnawave VPN stack — designing, generating, or debugging
  selfsteal nodes built on VLESS + Reality + XTLS-Vision (Xray-core), Caddy selfsteal
  masking, and mihomo (Clash.Meta) client configs. Triggers on: Remnawave panel/node,
  selfsteal, Reality/Vision handshake, xray config, Caddyfile, mihomo/clash yaml,
  "нода не подключается", "Reality палится", "handshake fail", генерация конфигов нод.
  Covers stack reference, config generation with validated defaults, and
  symptom→cause→fix diagnostics.
---

# Remnawave Stack — selfsteal-ноды (Xray Reality + Caddy + mihomo)

Скилл под конкретный стек: **Remnawave** (оркестратор панель→нода) → **Xray-core**
(VLESS+Reality+XTLS-Vision на ноде) → **Caddy** (selfsteal-заглушка на той же машине) →
**mihomo/Clash.Meta** (клиент). Три режима: справочник, генератор конфигов, диагностика.

Данные собраны из первоисточников (исходники XTLS/Xray-core, wiki mihomo, docs.rw,
selfsteal.sh DigneZzZ) на 2026-07-01. Факты, помеченные в подфайлах как «НЕТОЧНО» —
проверять под свою версию.

## Когда использовать

- Поднять/починить selfsteal-ноду (Xray Reality + Caddy на одном сервере).
- Сгенерировать рабочий конфиг: Xray inbound, Caddyfile, mihomo yaml.
- Разобрать симптом: нода offline, Reality палится/handshake fail, Caddy 502, mihomo не коннектится.
- Не запутаться в специфике: порты, ключи, что с чем совпадает, что выпилено из ядра.

## Архитектура в двух словах

```
                         :443 (0.0.0.0)
  клиент mihomo ──TLS──►  Xray-core (VLESS+Reality+Vision)
                            │
              Reality-auth OK ├─► расшифровка VLESS, проксирование трафика юзера
                            │
              auth FAIL ─────┴─► прозрачный форвард (raw TCP + PROXY-proto xver:1)
                                  ──► Caddy  :9443 (127.0.0.1)  ──► реальный сайт-заглушка
                                      Caddy :80 (0.0.0.0) держит ACME HTTP-01 сам
```

Смысл selfsteal: `dest` Reality = **твой собственный** домен с настоящим ACME-сертом и
реальным сайтом за Caddy. Активный пробинг видит обычный сайт — неотличимо. Детали и
таблица портов → `reference/architecture.md`.

## Железные инварианты (нарушишь — не работает или палится)

1. **Порт 443.** Не-443 ядро само помечает warning'ом → быстрый бан IP. Слушать только 443.
2. **Согласованность selfsteal:** `realitySettings.dest` → локальный Caddy (напр. `127.0.0.1:9443`);
   `serverNames` == `SELF_STEAL_DOMAIN`; `SELF_STEAL_PORT` совпадает в Caddyfile (`https_port`)
   и в Xray `dest`. Разъехались — handshake или заглушка ломаются.
3. **Домен selfsteal — DNS-only (серое облако), НЕ под Cloudflare-proxy.** Оранжевое облако
   терминирует TLS у себя, ключа Reality не имеет → ломает и ACME, и сам Reality. (Не путать
   с отдельной техникой Reality+CDN/XHTTP — это другой инбаунд, см. xray-reality.md.)
4. **Flow только `xtls-rprx-vision`**, одинаковый на сервере и клиенте, только поверх raw TCP.
   Legacy XTLS-flow (`-direct/-splice/-origin`) — мёртвая ошибка в коде.
5. **Клиент (mihomo): `client-fingerprint` обязателен** при `reality-opts` — без него handshake
   не поднимется (`REALITY is based on uTLS...`). `global-client-fingerprint` выпилен в 1.19.27 —
   только per-proxy.
6. **Ключи:** privateKey/publicKey — ровно 32 байта; publicKey клиента = `xray x25519 -i "<server privateKey>"`;
   shortId ≤16 hex, чётная длина; на клиенте — единственное число `serverName`/`shortId`
   (множественное = ошибка парсинга).
7. **Никаких `apple`/`icloud` в `serverNames`** (ядро выдаёт warning + бан по GFW). Никакого `allowInsecure`
   (выпилен в v26.2.6). `show: false` в проде.
8. **Инфра ноды:** `network_mode: host` для Xray и Caddy; порт **80** открыт (ACME); порт ноды
   (control-API панель→нода) открыт только для IP панели; связь панель→нода двухслойная (mTLS + JWT RS256,
   `SECRET_KEY` = base64-JSON с сертами). Внутренний API Xray — `127.0.0.1:61000`/unix-socket (не «61001»), не трогать.

## Куда смотреть

| Задача | Файл |
|---|---|
| Как устроена нода, порты, потоки данных, xver/proxy_protocol | `reference/architecture.md` |
| Reality/Vision: параметры, dest, ключи, post-quantum, анти-пробинг, что выпилено | `reference/xray-reality.md` |
| Caddy selfsteal: Caddyfile, ACME, listener_wrappers, DNS-only домен | `reference/caddy-selfsteal.md` |
| mihomo клиент: yaml, VLESS+Reality запись, DNS/rules/sniffer/tun, грабли | `reference/mihomo.md` |
| Панель: Config Profile→Inbound→Host, node-agent, автогенерация pubkey | `reference/remnawave.md` |
| Другие транспорты: xhttp / ws / grpc / httpupgrade / mkcp / hysteria (HY2) | `reference/transports.md` |
| Другие протоколы: vmess / trojan / ss / wireguard / VLESS-Encryption + статус HY2/TUIC/AnyTLS | `reference/protocols.md` |
| Сгенерировать конфиг под параметры + команды ключей | `generators.md` |
| Что-то не работает / палится → симптом→причина→фикс | `diagnostics.md` |
| Готовые обезличенные боевые шаблоны (selfsteal / CDN-мост / балансир / mihomo / SRR) | `examples/` |

## Версии стека (на 2026-07-01 — сверять перед деплоем)

| Компонент | Версия | Формат |
|---|---|---|
| Remnawave panel/node | 2.8.0 (2026-06-29) | semver |
| Xray-core | v26.6.27 | CalVer `vYY.M.D` |
| Caddy | 2.11.4 | semver |
| mihomo (Clash.Meta) | 1.19.27 | линейка `v1.19.x` |

## Режимы

- **Справочник** — вопрос по стеку: открыть нужный `reference/*.md`, ответить по факту, не по памяти.
- **Генератор** — нужен конфиг: `generators.md`, заполнить плейсхолдеры, прогнать чеклист согласованности.
- **Диагностика** — сломано: `diagnostics.md`, от симптома к причине, дать команды проверки.
