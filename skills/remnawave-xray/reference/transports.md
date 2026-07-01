# Xray-транспорты (streamSettings.network)

Транспорт — как оборачивается протокол (VLESS/VMess/Trojan/Shadowsocks). `raw` покрыт в
`xray-reality.md`. Здесь остальные. Сверено с офиц. xtls.github.io; XHTTP/hysteria свежие —
уровень доверия помечен.

## Матрица security x network (жёсткое ограничение)

| security | Совместимые транспорты |
|---|---|
| `reality` | **только** `raw`, `xhttp`, `grpc` |
| `tls` | все (`raw`, `xhttp`, `mkcp`, `grpc`, `websocket`, `httpupgrade`, `hysteria`) |
| `none` | любой (без шифрования транспорта — только за CDN/локально) |

`flow: xtls-rprx-vision` — **только `raw`**. Reality поверх XHTTP/gRPC → `flow` НЕ указывать.

## Когда что

| Транспорт | Когда | Детект/минус |
|---|---|---|
| `raw` (+Reality) | дефолт для прямых нод, макс. маскировка | — (эталон) |
| `xhttp` | за CDN (Cloudflare/фронт), гибкий HTTP/2-3, padding | сложность, спека нестабильна |
| `websocket` | за CDN, широкая совместимость клиентов | fingerprint `ALPN=http/1.1`, офиц. рекомендуют XHTTP |
| `httpupgrade` | легче WS за CDN (без двусторонней рамки WS) | тоже рекомендуют XHTTP |
| `grpc` | за CDN/H2-инфра, мультиплекс | нет fallback по пути, active-probe риск |
| `mkcp` | UDP, высокие потери/пинг (мобильные) | не за CDN, характерный трафик |
| `hysteria` | QUIC/UDP, потери/дальние линки, port-hopping | свежее (см. ниже), QUIC палится по-своему |

## XHTTP (`xhttpSettings`) — flagship для CDN

Офиц. reference-страницы НЕТ, спека в [Discussion #4113](https://github.com/XTLS/Xray-core/discussions/4113)
(автор RPRX). **Уровень доверия: средний — API меняется, сверять перед использованием.**

- `host`, `path` (обяз., совпадает на upload/download), `mode`:
  `auto` (TLS+H2→stream-up; REALITY→stream-one; иначе packet-up) | `packet-up` | `stream-up` | `stream-one`.
- `extra`:
  - `xmux`: `maxConcurrency` (напр. `"16-32"`), `maxConnections`, `cMaxReuseTimes`, `cMaxLifetimeMs`,
    `hMaxRequestTimes`, `hMaxReusableSecs`, `hKeepAlivePeriod`.
  - padding/obfs: `xPaddingBytes` (`"100-1000"`), `xPaddingKey/Header/Method/Placement/ObfsMode`,
    `uplinkHTTPMethod`, `noGRPCHeader`, `noSSEHeader`, `scMaxEachPostBytes`, `scMinPostsIntervalMs`,
    `scMaxBufferedPosts`, `scStreamUpServerSecs`, `downloadSettings`.

**Боевой пример** (`../examples/xray-cdn-bridge.json`, RU-XHTTP-CDN): `listen: 127.0.0.1`, `security: none`
(TLS терминирует CDN/реверс-прокси спереди), `host: <CDN_FRONT_HOST>`, `mode: packet-up`, `path` под
легитимный API-путь, `xmux.maxConcurrency: "16-32"`, padding `xPaddingMethod: tokenish`,
`xPaddingPlacement: queryInHeader`, `uplinkHTTPMethod: GET`.

## WebSocket (`wsSettings`)

`path` (deflt `/`, поддерживает `?ed=2560` — Early Data), `host`, `headers` (только клиент),
`heartbeatPeriod` (0 = не слать Ping), `acceptProxyProtocol` (inbound). Обычно `security: none` за CDN
(TLS у CDN) или `tls`. Пример в `../examples/xray-cdn-bridge.json` (RU-WS-CDN, path под Next.js/API).

## gRPC (`grpcSettings`)

`serviceName`, `authority`, `multiMode` (BETA, deflt false), `user_agent`, `idle_timeout` (сек, min 10),
`health_check_timeout` (deflt 20), `permit_without_stream` (deflt false), `initial_windows_size` (deflt 0).
Fallback по пути не умеет — риск active-probing без TLS-обёртки.

## HTTPUpgrade (`httpupgradeSettings`)

`path` (deflt `/`), `host`, `headers`, `acceptProxyProtocol`. Легче WS (одностороннее HTTP Upgrade),
за CDN. Офиц. тоже подталкивают к XHTTP.

## mKCP (`kcpSettings`)

UDP-транспорт для линков с потерями. Поля: `mtu` (~1350), `tti` (~50мс), `uplinkCapacity`/`downlinkCapacity`
(Мбит), `congestion` (bool), `readBufferSize`/`writeBufferSize` (МБ), `seed` (пароль обфускации),
`header.type` (обфускация под трафик: `none`/`srtp`/`utp`/`wechat-video`/`dtls`/`wireguard`). Жрёт больше
CPU/полосы, не за CDN. **Проверять актуальные дефолты под версию.**

## Hysteria (`network: "hysteria"` + `hysteriaSettings`) — QUIC/HY2

Полноценный **Hysteria 2 в ядре**: outbound+transport с **v26.1.23**, inbound+transport с **v26.3.27**.
`protocol: "hysteria"` жёстко `version: 2` (иначе ядро отклоняет старт). Требует **настоящий TLS-серт**
(`security: tls` + `tlsSettings.certificates`) — Reality тут не при чём.

Поля (settings — уровень протокола; hysteriaSettings — транспорт):
- `settings`: inbound — `version: 2`, `clients[].auth`/`email`/`level`; outbound — `version: 2`, `address`, `port`.
- `streamSettings.hysteriaSettings`: `version: 2`, **`auth`** (на клиенте пароль идёт СЮДА, не в `settings`!),
  `up`/`down` (напр. `"100mbps"`/`"300mbps"`; единицы bps/kbps/mbps/gbps/tbps), `udpIdleTimeout` (2-600, deflt 60),
  `udphop` (port hopping), **`masquerade`** (`{type:"file", dir:"/var/www"}` — отдаёт реальный сайт неавторизованным,
  HY2-аналог selfsteal).
- **QUIC-параметры унифицированы в `streamSettings.finalmask.quicParams`** (v26.3.27+): `congestion`
  (reno/bbr/brutal/force-brutal; hysteria дефолт **brutal**), `brutalUp`, `brutalDown` (Мбит), `udpHop`. Старые
  одноимённые поля в `hysteriaSettings` — soft-deprecated (ядро пишет warning).
- **Salamander-обфускация** — через `finalmask` (Salamander finalmask; Finalmask шире Salamander).
- **Port hopping**: inbound слушает ОДИН порт, остальные порты диапазона форвардятся `iptables` на него.
- **Клиент mihomo**: `type: hysteria2`, `ports: 443-8443` + `hop-interval` (port hopping), `password`, `up`/`down`,
  `obfs: salamander` + `obfs-password`, `sni`, `skip-cert-verify`, `alpn: [h3]`.
- Шероховатости (молодая фича): рассинхрон Salamander, HY2 inbound иногда принимает UDP но не отвечает (таймаут
  #5921), не трекается в online-stats. На критичном проде тестировать.

Пример сервера (из core-tutorial):
```json
{ "tag": "hy2-in", "listen": "0.0.0.0", "port": 443, "protocol": "hysteria",
  "settings": { "version": 2, "clients": [{ "auth": "<PASS>", "email": "user" }] },
  "streamSettings": { "network": "hysteria", "security": "tls",
    "tlsSettings": { "certificates": [{ "certificateFile": "/etc/ssl/cert.pem", "keyFile": "/etc/ssl/key.pem" }] },
    "hysteriaSettings": { "version": 2, "masquerade": { "type": "file", "dir": "/var/www" } },
    "finalmask": { "quicParams": { "congestion": "brutal", "brutalUp": 100, "brutalDown": 300 } } } }
```

## Congestion control (`finalmask.quicParams.congestion`)

`reno` / `bbr` / `brutal` / `force-brutal`. Дефолты: XHTTP поверх H3 → `bbr`; Hysteria → `brutal`
(требует задать `brutalUp`/`brutalDown` — фиксированная полоса, отсюда стабильность на потерях).

Матрица/flow → `xray-reality.md`. Протоколы (что кладётся В транспорт) → `protocols.md`.