# Routing и outbound: сплит-туннель, гео-разблок, WARP

Где живёт роутинг: **на клиенте** (клиентский Xray/mihomo — что в туннель, что напрямую) и
**на ноде** (Config Profile — блок приватных сетей, torrent, connectivity-check). Матчинг —
`type: "field"`, правила проверяются **сверху вниз, побеждает первое совпавшее**. Эталоны:
`examples/xray-client-ru-routing.json` (клиент, РФ-сплит), `examples/xray-selfsteal-node.json`
(нода, базовые block-правила), `examples/xray-balancer-*.json` (балансировщики в подписке).

## Анатомия правила

| Поле | Смысл |
|---|---|
| `domain` | список доменных матчеров (см. префиксы ниже) |
| `ip` | CIDR или `geoip:*` (`geoip:private`, `geoip:ru`, `geoip:cn`) |
| `port` / `sourcePort` | `443`, `1000-2000`, `53` |
| `network` | `tcp` / `udp` / `tcp,udp` |
| `protocol` | из sniffing: `http` / `tls` / `quic` / `bittorrent` |
| `inboundTag` / `outboundTag` | привязка к тегам инбаунда/аутбаунда |
| `source` / `user` / `attrs` | IP источника / email юзера / атрибуты HTTP |

`domainStrategy` (в блоке `routing`): `AsIs` (только домены, без резолва), `IPIfNonMatch` (не сматчил
доменом — резолвит и пробует по IP), `IPOnDemand` (резолвит сразу). Для сплит-туннеля обычно
`IPIfNonMatch`. `queryStrategy` в DNS — `UseIP` / `UseIPv4` / `UseIPv6`.

### Префиксы доменных матчеров

- `domain:example.com` — сам домен и все поддомены (рекомендуемый дефолт).
- `full:example.com` — **точное** совпадение, без поддоменов.
- `keyword:goog` — подстрока (широко, осторожно).
- `regexp:.*\.ru$` — регэксп (дорого, но незаменим для зон).
- `geosite:category-ru` / `geosite:openai` / `geosite:google` — списки из `geosite.dat`.
- Без префикса — трактуется как `keyword` (частый баг: `avito.ru` без `domain:` ловит лишнее).

## Сплит-туннель РФ (клиент)

Идея: РФ-домены/IP → `DIRECT`, всё остальное → `proxy`; connectivity-check → `DIRECT` (иначе капча
и «нет интернета» при поднятии). Порядок в `examples/xray-client-ru-routing.json`:

1. `port: 53 -> DIRECT` — DNS мимо прокси.
2. connectivity-check домены (`cp.cloudflare.com`, `msftconnecttest.com`, `captive.apple.com`, ...) → `DIRECT`.
3. РФ: `geosite:category-ru` + `regexp:.*\.ru$` + `.xn--p1ai$` + список крупных сервисов (Яндекс/VK/Сбер/
   маркетплейсы/банки/онлайн-кинотеатры) → `DIRECT`.
4. РФ-IP-диапазоны (Яндекс/VK ASN CIDR) → `DIRECT` — для случаев, когда домен не сматчился.
5. `geoip:private -> BLOCK`.
6. остальное `tcp,udp -> proxy`.

**Почему и домены, и IP:** `geosite:category-ru` покрывает домены, но сервис может ходить на IP без DNS
(мобильные API, WebRTC). CIDR-правило добивает. При росте — тянуть готовые листы (antifilter, ITDog,
`geosite:category-ru`), не поддерживать руками.

## Гео-разблок: сервисы, режущие по IP сервера

OpenAI/ChatGPT, Google Gemini/AI Studio, Spotify, часть банк-антифрода — блокируют **по IP выходной
ноды** (датацентр/страна), даже когда туннель работает. Лечится маршрутизацией таких доменов в
**чистый** outbound (WARP или отдельная резидентная нода):

```json
{ "type": "field",
  "domain": ["geosite:openai", "geosite:google", "domain:spotify.com", "domain:scdn.co"],
  "outboundTag": "warp" }
```

Правило ставить **выше** общего `-> proxy`. `geosite:openai`/`geosite:google` берутся из свежего
`geosite.dat` — если устарел, домены не сматчатся (см. «Гео-файлы» ниже).

## WARP как чистый outbound (WireGuard)

Cloudflare WARP даёт бесплатный резидентный-ish выход, удобен под гео-разблок. Ключи — `wgcf`
(`wgcf register && wgcf generate`), из профиля берутся `PrivateKey`, `Address`, `PublicKey`
(`engage.cloudflareclient.com:2408`). Outbound в Xray:

```json
{ "tag": "warp", "protocol": "wireguard",
  "settings": {
    "secretKey": "<WGCF_PRIVATE_KEY>",
    "address": ["172.16.0.2/32", "2606:4700:110:xxxx::/128"],
    "peers": [{ "publicKey": "bmXOC+F1FxEMF9dyiK2H5/1SUtzH0JuVo51h2wPfgyo=",
                "endpoint": "engage.cloudflareclient.com:2408",
                "allowedIPs": ["0.0.0.0/0", "::/0"] }],
    "mtu": 1280 } }
```

**Цепочка «через основной прокси, потом WARP»** (WARP видит не IP клиента, а IP выходной ноды) —
`dialerProxy` на streamSettings WARP-аутбаунда указывает на тег основного прокси-аутбаунда:

```json
"streamSettings": { "sockopt": { "dialerProxy": "proxy" } }
```

Так пакет идёт клиент → нода (Reality) → WARP → OpenAI. Без `dialerProxy` WARP цепляется напрямую
с машины, где крутится этот Xray. На ноде Remnawave WireGuard-outbound кладётся в Config Profile;
на клиенте — в клиентский конфиг.

Альтернатива WARP — **вторая нода** резидентного IP как Reality/VLESS-outbound (`serverName` = её домен,
`password` = её pubkey), тем же приёмом через `outboundTag`.

## Реклама / трекеры / малварь (опц.)

`geosite:category-ads-all -> BLOCK` (blackhole). На ноде экономит трафик, на клиенте — блок рекламы.
Не блокировать `geosite:category-ads` вслепую на банк/маркетплейс-доменах — бывают ложные срабатывания.

## Гео-файлы (geoip.dat / geosite.dat)

- Матчеры `geoip:*` / `geosite:*` работают только с актуальными `.dat`. Протухший `geosite.dat` не
  знает свежих доменов (новые OpenAI/сервисные) → правило молча не срабатывает.
- **Нода Remnawave:** монтировать **по одному файлу** в `/usr/local/share/xray/` (том на директорию
  затрёт дефолтные) — см. `reference/remnawave.md`.
- Источники: `Loyalsoldier/v2ray-rules-dat`, `runetfreedom/russia-*` (РФ-специфика). RU-`geoip` дрейфует
  (новые ASN), поэтому для РФ надёжнее доменные правила + периодически обновляемые CIDR-листы.

## Грабли

1. **Порядок правил.** Block-правила (private/torrent) — выше разрешающих. Первое совпадение выигрывает.
2. **DNS в цикле.** `port: 53 -> DIRECT` (или в чистый резолвер), иначе DNS-запросы уходят в прокси,
   который резолвится через... DNS — петля. На клиенте держать `default-nameserver`/`servers` на IP.
3. **`geoip:private` не в BLOCK** → внутрянка (роутер, NAS) утекает в туннель.
4. **Матчер без префикса** = `keyword` (подстрока), не домен. Для домена всегда `domain:`/`full:`.
5. **`dialerProxy` забыт** на WARP-цепочке → гео-разблок идёт с IP ноды, а не «клиент→нода→WARP», толку ноль.

Клиентский DNS/rules mihomo → `reference/mihomo.md`. Транспорты аутбаундов → `reference/transports.md`.
Проверка итогового конфига → `python validate.py <config.json>` и `diagnostics.md`.