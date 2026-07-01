# Xray-протоколы (inbound/outbound.protocol)

Что есть В Xray-core — ground truth из `infra/conf/xray.go` (таблица регистрации `protocol`).
VLESS+Reality покрыт в `xray-reality.md`.

## Что реально в Xray-core (и чего нет)

| Протокол | В Xray? | Примечание |
|---|---|---|
| vless, vmess, trojan, shadowsocks | ✅ | vmess/trojan/ss помечены deprecated (nudge → VLESS Encryption, но не удалят) |
| **hysteria** (=Hysteria 2) | ✅ | `version: 2` жёстко. out с v26.1.23, in с v26.3.27. Конфиг → `transports.md` |
| wireguard (in+out) | ✅ | для WARP/цепочек |
| socks, http, dokodemo-door(`tunnel`), mixed, tun | ✅ | локальные/клиентские |
| freedom(`direct`), blackhole, dns, loopback, block | ✅ | служебные outbound |
| **TUIC** | ❌ НЕТ | протокол sing-box, в Xray не регистрируется |
| **AnyTLS** | ❌ НЕТ | issue #4428 «not planned»; живёт в `anytls/anytls-go`, понимает sing-box |
| Shadowsocks obfs (SIP003) | ❌ НЕТ | оборачивать SS в ws/grpc/xhttp+TLS |

## VLESS Encryption (post-quantum) — кладётся под что угодно

PR #5067, в релизе с **v25.8.31**. Поля `decryption` (inbound) / `encryption` (outbound) — отдельно от
старого `"none"`. Формат: `<handshake>.<mode>.<rtt>.<pad1>.<pad2>.<pad3>.<key>`, где handshake пока только
`mlkem768x25519plus` (ML-KEM-768 + X25519), mode `native`/`xorpub`/`random`, rtt `0rtt`/`1rtt`.
Генерация: **`xray vlessenc`** (пара сразу) или `xray mlkem768`/`xray x25519`.

- **Совместим с любым** streamSettings: Reality, Vision, TLS, даже `security: none`.
- **НЕ инструмент обхода** (слова RPRX) — даёт PFS + защиту UUID/метаданных от CDN/relay-посредников. Для
  обхода GFW по-прежнему Reality/Vision/XHTTP. Молодая фича (~с авг 2025), wire-format ещё устаканивается.

## Hysteria 2 (нативный)

`protocol: "hysteria"`, `version: 2`. Salamander-обфускация + port-hopping в `finalmask`, congestion `brutal`.
Полный разбор полей и каркас конфига → `transports.md` (раздел Hysteria). Реализация свежая, есть баги —
на критичном проде тестировать. **Remnawave 2.8.0 умеет HY2 штатно**: backend получил генерацию HY2-ссылок
(`XrayGeneratorService`) и HY2 в mihomo-подписке (`MihomoGeneratorService`). Настраивается как обычный
`hysteria` inbound в Config Profile → активировать на ноде → привязать Host. Нужен настоящий TLS-серт на ноде
(Let's Encrypt/Caddy), Reality не используется. Гайды: teletype `@idsmef`, docs.rw config-profiles.

## Legacy (для совместимости, новое не строить)

- **VMess** — `clients[].id`, `security` (auto/aes-128-gcm/chacha20-poly1305/none/zero). `alterId` выпилен.
  Deprecation-warning в логе. Детектируемость выросла.
- **Trojan** — `clients[].password` + `fallbacks[]` (dest/alpn/path/xver). **`flow` полностью убран** (hardfail
  если непустой — Vision поверх Trojan больше нет). Проще VLESS (пароль + fallback на реальный веб), хорош для
  интеропа со сторонними Trojan-клиентами.
- **Shadowsocks** — `method`: `2022-blake3-aes-128/256-gcm`, `2022-blake3-chacha20-poly1305`, `aes-256-gcm`,
  `chacha20-poly1305`, `xchacha20-poly1305`, `none`. `network` tcp/udp/tcp,udp. SS-2022 мульти-юзер:
  `password` = `ServerPSK:UserPSK`. Deprecation-warning на любой метод (не удалят). obfs нет.

## WireGuard (outbound для WARP/цепочек)

`secretKey` (hex/base64), `address[]` (CIDR), `peers[]` (`publicKey`, `endpoint`, `allowedIPs` deflt
`0.0.0.0/0,::0/0`, `preSharedKey`, `keepAlive`), `mtu` (1420), `reserved` (пусто или 3 байта — для Cloudflare
WARP), `noKernelTun`, `domainStrategy` (только `forceip*`). **streamSettings НЕ поддерживается** (свой UDP-фрейминг).
Типовое: WARP-outbound (`endpoint: engage.cloudflareclient.com:2408`) как `outboundTag` на нужные домены/хоп цепочки.

## Локальные inbound (клиентский конфиг)

- **socks**: `auth` (noauth/password), `users[]`, `udp`. **http**: Basic-auth, `allowTransparent`.
- **dokodemo-door** (=`tunnel`): `address`/`port`, `followRedirect` (для iptables REDIRECT/TPROXY — прозрачный прокси).

Пример клиентского socks/http (10808/10809) → `../examples/xray-client-ru-routing.json`.

## Freedom / Blackhole (служебные outbound)

- **Freedom** (`direct`): `domainStrategy`, `redirect`, `fragment` (**`packets: "tlshello"`** — фрагментация
  TLS ClientHello против DPI, встроенный анти-цензурный трюк), `noises[]`, `proxyProtocol`, `finalRules[]`.
- **Blackhole**: `response.type` none/http — дроп трафика (adblock, гео-блок, kill-switch через routing).

## TUIC / AnyTLS — не в Xray, что делать

Серверная нода Remnawave = Xray → **TUIC и AnyTLS ей не поднять** (их в Xray нет). Варианты:
- Отдельное ядро рядом (sing-box, anytls-go) отдельным контейнером на ноде — **вне штатного Remnawave-флоу**;
  Remnawave-нода запускает только Xray, этим сервером панель не управляет и в подписку штатно не заведёт.
- **Клиентски** mihomo и sing-box умеют hysteria2/tuic/anytls (proxy-записи). Но серверный аутбаунд должен реально
  существовать — а Xray-нода серверно даёт из этого только HY2.

Практический вывод: из «новых UDP/обфускация-протоколов» в связке Remnawave+Xray серверно доступен **Hysteria 2**
(штатно с 2.8.0 — `Xray`/`Mihomo` генераторы ссылок); TUIC/AnyTLS — только сознательно на отдельном ядре вне панели.

## Когда что выбирать

- **Reality (raw+Vision)** — дефолт: TCP, максимальная маскировка, обкатано. Первый выбор.
- **Hysteria 2 / mKCP** — UDP/QUIC: лучше на потерях/дальних/мобильных линках, port-hopping против блокировки
  портов. Минус: QUIC/UDP палится по объёму/паттерну, часть операторов режет UDP:443 (тогда QUIC-block в клиенте
  как в `../examples/mihomo-example.yaml`). HY2 в Xray свежий — тестировать.
- **VLESS Encryption** — не вместо Reality, а поверх: PFS + защита метаданных. Опционально.
- **Trojan / VMess / SS** — только для совместимости со сторонними клиентами/панелями. Новое не строить.
- **WireGuard** — выходной хоп / WARP / цепочки, не входная точка для юзеров.

Транспорты → `transports.md`. Reality → `xray-reality.md`. Генерация → `../generators.md`.