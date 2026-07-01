# Архитектура selfsteal-ноды

Каноническая схема «steal oneself»: Xray-core и Caddy — два независимых процесса/контейнера
на **одной** машине (ноде), оба в `network_mode: host`. Не конфликтуют по портам, потому что
каждый слушает своё. `dest` Reality заворачивает непрошедший авторизацию трафик на локальный
Caddy, который отдаёт настоящий сайт с настоящим ACME-сертом.

## Поток данных

```
  клиент (mihomo) ──TLS ClientHello (SNI = selfsteal-домен, uTLS-fingerprint)──► :443
                                                                                  │
                                                        Xray-core (VLESS+Reality+Vision)
                                                                                  │
                              ┌───────────── Reality AuthKey OK? ─────────────────┤
                              │ ДА                                          НЕТ  │
                              ▼                                                   ▼
             расшифровка VLESS, XTLS-Vision,                    прозрачный форвард raw TCP
             трафик юзера ──► freedom outbound ──► интернет      (+ PROXY-proto, если xver≥1)
                                                                                  │
                                                                                  ▼
                                                        Caddy :9443 (127.0.0.1), tls
                                                        реальный сайт-заглушка (ACME-серт)
                                                                                  │
                                    Caddy :80 (0.0.0.0) — ACME HTTP-01 + redirect →HTTPS
```

Ключевое: при провале авторизации пробер (сканер/DPI/случайный браузер) получает **настоящий
сертификат настоящего сайта** — от прямого захода на сайт неотличимо. Это и есть защита Reality
от активного пробинга по конструкции.

## Карта портов

| Кто | Порт | Bind | Назначение |
|---|---|---|---|
| **Xray VLESS+Reality** | **443** | `0.0.0.0` | публичный вход, единственный «боевой» порт |
| **Caddy — HTTP** | **80** | `0.0.0.0` | ACME HTTP-01 challenge + редирект на HTTPS; Caddy держит сам, Xray не участвует |
| **Caddy — HTTPS заглушка** | **`$SELF_STEAL_PORT`** (дефолт 9443) | `127.0.0.1` | реальный сайт за Reality `dest`; TLS терминирует настоящим сертом |
| **Caddy — catch-all** | тот же `$SELF_STEAL_PORT` | — | блок `:port { tls internal; respond 204 }` для запросов без валидного SNI |
| RemnaNode control-API | `NODE_PORT` (env, в примерах ~2222) | `0.0.0.0` | канал панель→нода; **firewall должен пускать только IP панели** |
| RemnaNode internal API Xray | `127.0.0.1:61000` / unix-socket | `127.0.0.1` | gRPC StatsService + авто-инбаунд `REMNAWAVE_API_INBOUND`; internal, не трогать (число «61001» — миф) |

## Почему `dest` → localhost Caddy, а не публичный чужой сайт

`realitySettings.dest` = `127.0.0.1:$SELF_STEAL_PORT` (Caddy), `serverNames` = твой домен.
Свой домен + свой серт + свой реальный сайт убирает главные детект-сигналы: несовпадение
IP/ASN/SNI, чужой аптайм, чужую ротацию серта. Альтернатива «угнать чужой популярный сайт»
слабее: `apple.com`, отвечающий с дешёвого VPS, палится репутационным анализом без взлома крипты
(ядро прямо warning'ит на `apple`/`icloud`). Подробнее про выбор dest → `xray-reality.md`.

## xver + PROXY protocol (зачем `listener_wrappers` в Caddy)

- `realitySettings.xver: 1` (или `2`) → при форварде на `dest` Xray добавляет заголовок
  **PROXY protocol** v1/v2 с реальным адресом клиента.
- Чтобы Caddy это распарсил, в его глобальном блоке нужен:
  ```
  servers 127.0.0.1:9443 {          # адресный скоуп ОБЯЗАТЕЛЕН
    listener_wrappers {
      proxy_protocol { allow 127.0.0.1/32 }
      tls
    }
  }
  ```
  Порядок важен: `proxy_protocol` до `tls`. **Адрес в `servers` обязателен** — пустой `servers { }`
  протекает враппером на ACME-порт `:80` → `400 Bad Request` (issue #5602). Тогда в логах Caddy виден
  реальный IP пробера, а не `127.0.0.1`.
- `xver: 0` → без PROXY protocol; тогда `listener_wrappers`-обёртку с `proxy_protocol` из Caddy
  надо убрать, иначе Caddy будет ждать заголовок, которого нет.

## Почему `network_mode: host`

Оба контейнера (Xray, Caddy) — в host-сети. Через bridge+NAT ломается PROXY protocol / реальный
IP и разъезжаются порты (Xray думает, что форвардит на `127.0.0.1:9443`, а Caddy за NAT слушает
не там). Host-режим убирает этот класс проблем.

## Топология развёртывания

- **Xray + Caddy selfsteal — всегда на одной машине** (ноде): `dest` = `127.0.0.1`, они обязаны
  быть локальны друг другу.
- **Панель** может (и в проде обычно должна) стоять отдельно от ноды. Направление связи —
  **панель → нода**: панель сама подключается к `NODE_PORT` и запускает на ноде Xray с присланным
  конфигом. Нода наружу к панели не ходит.
- Типичная прод-модель (гайд IadjustI): 3 роли — панель / нода(ы) / selfsteal-заглушка, где
  заглушка живёт на той же VPS, что и нода.

## Переменные (соглашение selfsteal.sh / ручных гайдов)

| Переменная | Смысл | Где используется |
|---|---|---|
| `SELF_STEAL_DOMAIN` | твой домен-заглушка (DNS-only!) | Caddyfile site-блок + Xray `serverNames` |
| `SELF_STEAL_PORT` | локальный HTTPS-порт Caddy | Caddyfile `https_port` + Xray `dest` |
| `CADDY_VERSION` | пин версии образа | docker-compose (дефолт 2.11.4) |
| `HTML_DIR` | папка со статикой сайта | volume Caddy → `/var/www/html` |

Смежное: конкретный Caddyfile → `caddy-selfsteal.md`; Reality-параметры → `xray-reality.md`;
привязка в панели (Config Profile→Inbound→Host) → `remnawave.md`.
