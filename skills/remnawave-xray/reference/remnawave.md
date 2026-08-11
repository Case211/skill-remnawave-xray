# Remnawave: панель, нода, подписки

Panel **3.2.3** / Node **3.1.1** (⇄ Xray-core v26.7.28). Сверено с исходниками `remnawave/backend`
на теге 3.2.3, Dockerfile ноды на теге 3.1.1 и форумом релизов; часть — с живой панели.

⚠️ **3.0.0 — мажор с ломающим API.** Всё, что ходило в панель по UUID пользователя, переписывается;
детали ниже в «Panel API v3». На конфиги Xray/Caddy это не влияет — ломается интеграция, не стек.

## Компоненты

| Компонент | Образ | Роль |
|---|---|---|
| Backend (панель) | `remnawave/backend:3` | NestJS API + БД-логика. Внутри PM2-кластер: `api` (масштаб `API_INSTANCES`), `scheduler`, `processor`. |
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
- **Host** = «шлюз» в подписке. Выбирает ровно один Inbound. Порт **наследуется** от инбаунда;
  пустые Advanced-поля → берутся из инбаунда. С 3.x у хоста есть собственное поле `nodes[]`
  (массив uuid, редактируемое в create/update) — привязка к нодам стала явной, а не только
  косвенной «через профиль». Старое правило «прямой связи host↔node нет» больше не верно.
- **Internal Squad** = группа доступа: какие Inbound'ы доступны юзеру (аддитивно, юзер в нескольких).
  **External Squad** (≥2.2.0) = переопределение Templates/Settings для группы.
- **Snippets** — переиспользуемые куски `outbounds`/`routing` across профилей (правишь раз — меняется везде).

## Поля Host (схема 3.2.3, `libs/contract/models/hosts.schema.ts`)

`remark`, `address` (домен предпочтительнее IP — при смене IP ноды подписки не переиздавать), `port` (наследуется),
`sni` (пусто → из `serverNames` инбаунда), `host`, `path`, `alpn`, `fingerprint`, `securityLayer` (DEFAULT/TLS),
`tags[]`, `isHidden` (не в обычной подписке — только через `injectHosts`), `isDisabled`, `pinnedPeerCertSha256`,
`verifyPeerCertByName` (cert-pinning), `mihomoX25519`/`mihomoIpVersion`, `overrideSniFromAddress`,
`keepSniBlank`, `excludedInternalSquads[]`, `excludeFromSubscriptionTypes[]`, `xrayJsonTemplateUuid`,
`viewPosition`, `inbound.{configProfileUuid, configProfileInboundUuid}`.

Появились к 3.2.3 (в снимке 2.8.0 их не было):

- `nodes[]` — явная привязка хоста к нодам (см. выше).
- `finalMask` — проброс объекта `finalmask` ядра (маскировка потока; в v26.7.28 к ней добавился XMC/Minecraft).
- `vlessRouteId` (0…65535) — идентификатор маршрута VLESS.
- `shuffleHost` — перемешивание.
- `serverDescription` (≤30 символов) — подпись сервера в клиенте.
- `xhttpExtraParams`, `muxParams`, `sockoptParams` — сырые объекты, уезжают в соответствующие секции конфига.
- **3.2.3:** `cipherSuites` из `tlsSettings` инбаунда теперь доезжает до Xray-Json и Base64-подписок
  (раньше терялся) — парная фича к «TLS client: support more cipherSuites for unsafe fingerprint» в v26.7.28.

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
- **Node 3.1.1: гео-файлы докачиваются самой нодой перед стартом ядра.** Раньше корректно описанный
  объект `geodata` в конфиге не спасал на первом запуске — Xray не мог скачать файлы, которых ещё нет,
  и падал. Теперь недостающее нода тянет сама, а дальнейшие обновления Xray делает по своему cron.
  Прочие правки 3.1.1: `webhookUrl` в плагине Torrent Blocker, фикс зависания процесса ядра.

## ENV панели (ключевое)

**`APP_SECRET`** (`openssl rand -hex 64`) — с 3.0.0 один секрет вместо пары `JWT_AUTH_SECRET` +
`JWT_API_TOKENS_SECRET`; старые имена панель 3.x не читает. Дальше — `FRONT_END_DOMAIN` (CORS),
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

## Panel API v3 — что сломалось при переходе с 2.8.x

Всё это про **интеграции** (боты, админки, экспортеры). Конфигов Xray и Caddy не касается.

- **Пользователь адресуется числовым `id`, поля `uuid` у него больше нет.** Все ручки `{uuid}` стали
  `{userId}`. Интеграции, хранившие UUID юзера, придётся перевязать.
- Точечные ручки поиска **удалены** (`by-telegram-id`, `by-email`, `by-tag`) → `GET /api/users/stream`
  с фильтрами `telegramId` / `email` / `tag`.
- `/api/ip-control` → **`/api/connections`**, параметр `userUuids` → `userIds`.
- `DELETE` отвечает **204/202 без тела** (было 200 с телом). Bulk-операции больше не возвращают
  `{ affectedRows: N }` — узнать, сколько зацепило, нечем.
- Поля подписки `profileTitle` / `profileUpdateInterval` / `supportLink` уехали **в заголовки ответа**.
- Доки на фиксированном пути `/api/backend-tools`; `SWAGGER_PATH` / `SCALAR_PATH` / `IS_DOCS_ENABLED` убраны.

Прежние гетчи, которые остались в силе: `tag` инбаунда — UPPERCASE; в `create_user` бывают скрытые 400;
`/api/bandwidth-stats/nodes` — даты только `YYYY-MM-DD`; Config Profile нормализует `network: raw` ↔ `tcp`
в клиентской ссылке для совместимости.

## Прочее в 3.2.x

- **Сниппеты приняли `geodata` и `dns`** + опциональный перезапуск затронутых нод после правки (3.2.3).
- `REDIS_USERNAME` в ENV; нодам можно назначать IP-адреса с разными флагами (3.2.3).

Xray-детали инбаунда → `xray-reality.md`. Как selfsteal-нода собирается физически → `architecture.md`.