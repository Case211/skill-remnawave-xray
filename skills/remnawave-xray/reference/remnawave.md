# Remnawave: панель, нода, подписки

Panel/Node **2.8.0** (⇄ Xray-core 26.6.27). Сверено с docs.rw + исходники + живая панель 2.8.0.

## Компоненты

| Компонент | Образ | Роль |
|---|---|---|
| Backend (панель) | `remnawave/backend:2` | NestJS API + БД-логика. Внутри PM2-кластер: `api` (масштаб `API_INSTANCES`), `scheduler`, `processor`. |
| Frontend | (в том же backend-образе) | React, отдельного контейнера в проде нет. |
| Node (RemnaNode) | `remnawave/node` | TS-агент, **гоняет Xray-core**. |
| Subscription-page | `remnawave/subscription-page` | человекочитаемая страница подписки, `APP_PORT=3010`. |
| xtls-sdk | npm `@remnawave/xtls-sdk` | обёртка над gRPC Xray-core API (крипто, pbk из privateKey). |

**Панель НЕ содержит Xray** — без ноды проксировать некуда. Prod compose = 3 сервиса:
`remnawave` (3000/3001), `remnawave-db` (`postgres:18.4`), `remnawave-redis` (`valkey:9-alpine`, unix-socket).

## Иерархия (ключевая ментальная модель)

```
Config Profile (полный Xray JSON) ──> Inbound(ы) ──> Host(ы) ──> отдаются в подписку
        │                                  │
        └── privateKey Reality здесь       └── Internal Squad включает Inbound(ы) юзеру
        └── активен на Node(ах)
```

- **Config Profile** = целый Xray-core JSON («шаблон» для ноды). Одна Нода ↔ ровно один активный Профиль;
  Профиль ↔ несколько Нод возможно. `clients: []` в инбаундах **всегда пустой** — панель инжектит юзеров
  динамически при пуше конфига на ноду. `privateKey` Reality живёт прямо в `realitySettings` профиля, из БД не выходит.
- **Inbound** — конкретный протокол внутри профиля (VLESS+Reality и т.п.), идентифицируется `tag`.
- **Host** = «шлюз» в подписке. Выбирает ровно один Inbound → косвенно привязан к Нодам, где профиль активен
  (прямой связи host↔node нет). Порт **наследуется** от инбаунда; пустые Advanced-поля → берутся из инбаунда.
- **Internal Squad** = группа доступа: какие Inbound'ы доступны юзеру (аддитивно, юзер в нескольких).
  **External Squad** (≥2.2.0) = переопределение Templates/Settings для группы.
- **Snippets** — переиспользуемые куски `outbounds`/`routing` across профилей (правишь раз — меняется везде).

## Поля Host (реальная схема 2.8.0)

`remark`, `address` (домен предпочтительнее IP — при смене IP ноды подписки не переиздавать), `port` (наследуется),
`sni` (пусто → из `serverNames` инбаунда), `host`, `path`, `alpn`, `fingerprint`, `securityLayer` (DEFAULT/TLS),
`tags[]`, `isHidden` (не в обычной подписке — только через `injectHosts`), `isDisabled`, `pinnedPeerCertSha256`,
`verifyPeerCertByName` (cert-pinning, 2.8.0), `mihomoX25519`/`mihomoIpVersion`, `overrideSniFromAddress`,
`keepSniBlank`, `excludedInternalSquads[]`, `excludeFromSubscriptionTypes[]`, `xrayJsonTemplateUuid`.

## Установка ноды

Только **2 ENV**: `NODE_PORT` (слушает internal API от панели; в примерах 2222, настраиваемо) + `SECRET_KEY`
(выдаёт панель). `SECRET_KEY` — это base64-JSON `{caCertPem, jwtPublicKey, nodeCertPem, nodeKeyPem}`: нода
поднимает HTTPS с **mTLS** (`minVersion TLSv1.3`, `rejectUnauthorized`) + поверх **JWT RS256**. Связь строго
**панель → нода** (панель — клиент). Firewall ноды: `NODE_PORT` открыть **только для IP панели**.

- Нет ENV `SSL_CERT`/`APP_PORT` у ноды. TLS-серты для TLS-транспортов монтируются со стороны панели
  (`/var/lib/remnawave/configs/xray/ssl/`), для Reality **не нужны**.
- **Порт 61001 — миф.** Реально внутренний control-API Xray: `127.0.0.1:61000` (gRPC StatsService, старые сборки)
  либо unix-socket. Нода авто-инжектит служебный инбаунд `REMNAWAVE_API_INBOUND` (`protocol: tunnel`, в UI не виден).
  Всё это loopback/socket — наружу не выставляется, в firewall не трогать.
- Гео-файлы монтировать **по одному файлу** в `/usr/local/share/xray/` (иначе затрёшь дефолтные). Логи Xray —
  том `/var/log/remnanode` + **обязателен logrotate**. CLI: `docker exec -it remnanode cli` (`--dump-config`), `xlogs`.

## ENV панели (ключевое)

`JWT_AUTH_SECRET`, `JWT_API_TOKENS_SECRET` (оба `openssl rand -hex 64`), `FRONT_END_DOMAIN` (CORS),
`SUB_PUBLIC_DOMAIN` (домен+путь подписки), `APP_PORT` (3000), `METRICS_PORT` (3001), `API_INSTANCES` (1/max),
`METRICS_USER`/`METRICS_PASS`, вебхуки (`WEBHOOK_ENABLED`/`WEBHOOK_URL`/`WEBHOOK_SECRET_HEADER` ≥32),
telegram-нотификации, `EXPIRATION_NOTIFICATIONS`/bandwidth — **брать из актуального `.env.sample`**, а не со
страницы docs (там устарело/неполно). Панель обязательно за reverse-proxy на `127.0.0.1`, на root-пути домена.

## Подписки

- Формат по User-Agent: **Mihomo** / **Xray-json** / **Sing-box** / **Base64** (fallback). Браузер → веб-страница.
- `pbk=` в `vless://` — публичный ключ, **выводится панелью из `privateKey`** инбаунда на лету (приватный не покидает
  профиль). Остальные параметры ссылки — проекция полей Host + фикс `encryption=none`/`flow=xtls-rprx-vision`.
- **Response Rules (SRR)** — упорядоченные правила по заголовкам запроса → `responseType`
  (`MIHOMO`/`XRAY_JSON`/`XRAY_BASE64`/`SINGBOX`/`STASH`/`BROWSER`/`BLOCK`/`SOCKET_DROP`...). Переопределяют External Squads.
  Эталон: `../examples/subscription-response-rules.json` (Happ/Karing/Shadowrocket/Mihomo/xray-checker + HWID-проверка).
- **`injectHosts`** (директива `remnawave` в XRAY_JSON-шаблоне, ≥2.6.3) — подставляет outbound'ы **скрытых** хостов
  (`isHidden`) по `selector` (`uuids`/`remarkRegex`/`tagRegex`/`sameTagAsRecipient`) для сборки балансировщиков/мостов
  на клиенте. Панель вырезает объект `remnawave` из итога. Эталон: `../examples/xray-balancer-leastload.json`,
  `../examples/xray-balancer-random.json` (`remnawave.injectHosts` + `burstObservatory` + `leastLoad`/`random` balancer).

## Прочее

- **Backup — НЕ встроен** (community-инструменты). Monitoring — Prometheus `/metrics` + Grafana dashboard **25064**.
- CLI панели (`docker exec -it remnawave cli`): reset superadmin, enable password auth, **Get SECRET_KEY for Node**, reset certs.
- **Node Plugins** (≥2.7.0): Torrent Blocker (webhook Xray PR #5722, нужен Xray ≥26.3.27), Ingress/Egress Filter,
  Connection Drop — требуют `cap_add: NET_ADMIN` + nftables + ядро ≥5.7.

## Интеграционные gotchas (из практики remnawave-admin)

- Panel API: `tag` инбаунда — UPPERCASE; в `create_user` бывают скрытые 400. `/api/users/resolve` может
  отсутствовать (fallback на by-username/by-uuid). `/api/bandwidth-stats/nodes` — даты только `YYYY-MM-DD`.
- Config Profile нормализует `network: raw` ↔ `tcp` в клиентской ссылке для совместимости.

Xray-детали инбаунда → `xray-reality.md`. Как selfsteal-нода собирается физически → `architecture.md`.