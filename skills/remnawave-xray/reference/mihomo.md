# mihomo (Clash.Meta): клиентский конфиг

mihomo **v1.19.27** (линейка `v1.19.x`). Наследник Clash/Clash.Meta (Clash более не поддерживается).
Синтаксис — wiki.metacubex.one. Компактный образец: `../examples/mihomo-example.yaml`.

## Верхнеуровневые ключи config.yaml

`mixed-port` (HTTP+SOCKS на одном), `mode` (rule/global/direct), `proxies`, `proxy-groups`,
`proxy-providers`, `rules`, `rule-providers`, `dns`, `sniffer`, `tun`, `listeners`, `ntp`.
Geo — плоские ключи (`geodata-mode`, `geox-url`, `geo-auto-update`), отдельного блока `geodata:` нет.

## VLESS + Reality + Vision (proxy-запись)

```yaml
proxies:
  - name: "de-reality"
    type: vless
    server: <DE_NODE_DOMAIN>
    port: 443
    uuid: <CLIENT_UUID>
    network: tcp                 # для Reality; xhttp/ws/grpc — по инбаунду
    tls: true
    udp: true
    flow: xtls-rprx-vision       # единственный актуальный flow
    servername: <DE_NODE_DOMAIN> # SNI
    client-fingerprint: chrome   # ОБЯЗАТЕЛЕН при reality-opts (см. грабли)
    reality-opts:
      public-key: <REALITY_PUBLIC_KEY>
      short-id: <SHORT_ID>
      support-x25519mlkem768: true   # опц. post-quantum, сверять с сервером
```

## DNS (best practice)

```yaml
dns:
  enable: true
  enhanced-mode: fake-ip
  fake-ip-range: 198.18.0.1/16
  fake-ip-filter: ["+.lan","+.local","captive.apple.com","+.stun.*.*", ...]  # captive/STUN/NTP/gaming
  default-nameserver: [77.88.8.8, 1.1.1.1]          # ТОЛЬКО голые IP (бутстрап)
  proxy-server-nameserver: [https://...]            # резолв хостов proxy-серверов, рвёт петлю
  nameserver: [https://cloudflare-dns.com/dns-query, https://dns.google/dns-query]
  nameserver-policy: { "rule-set:geosite-ru": [tls://77.88.8.8], ... }
```

- `default-nameserver` — **только IP**, иначе бутстрап-петля.
- Резолв хоста своего прокси через `proxy-server-nameserver`, иначе «нет DNS без прокси, нет прокси без DNS».
- `fake-ip` требует полного перехвата (TUN/системный прокси), иначе часть софта получит нерабочий `198.18.x.x`.

## sniffer / tun / rule-providers

- `sniffer`: `sniff: {HTTP:{ports:[80,...]}, TLS:{ports:[443,...]}}`, `override-destination` (per-протокол перекрывает глобальный).
- `tun`: `stack: mixed` (TCP=system, UDP=gvisor), `auto-route`, `dns-hijack: ["any:53"]`, `strict-route`.
  Приём эталона: `exclude-package` — список РФ-банк/госприложений, которые всегда мимо TUN.
- `rule-providers`: `behavior` (`domain`/`ipcidr`/`classical`) + `format` (`yaml`/`text`/`mrs`; `mrs` только domain/ipcidr).
  **Нельзя мешать IP-CIDR в файл с `behavior: domain`** — ломает распознавание всех доменов файла (issue #1400).
  Есть `type: inline` (payload прямо в конфиге).

## Remnawave-ключи в шаблоне подписки (из docs.rw)

YAML-расширение `remnawave:` — панель раскрывает его при генерации подписки:

- `proxy-providers[*].remnawave.include-proxies: true` — авто-добавить прокси юзера (для chain).
- `proxy-groups[*].remnawave.include-proxies: false` — исключить авто-добавление в группу.
- `remnawave.select-random-proxy: true` — добавить один случайный хост юзера в группу.
- `remnawave.shuffle-proxies-order: true` — случайный порядок хостов при каждом обновлении + авто-failover.

Эталон использует `remnawave: {include-proxies: true}` в группах авто-выбора/RU-сайтов и `hidden: true`
у служебных групп `PROXY` / авто-выбора по пингу (`url-test`, `exclude-filter`).

## Что в образце (`../examples/mihomo-example.yaml`)

Компактный валидный скелет на **публичных** rule-sets (legiz-ru / Davoyan / itdoginfo / MetaCubeX):
- **fake-ip DNS** с анти-петлёй (`default-nameserver` только IP, `proxy-server-nameserver` для хостов прокси).
- **РФ-раздельный роутинг**: `geosite-ru`/`geoip-ru` (Davoyan) → DIRECT, заблокированное (`ru-inside` itdoginfo,
  `refilter` legiz) → proxy, реклама (`oisd`) → REJECT.
- **QUIC-блок**: `AND,((NETWORK,UDP),(DST-PORT,443)),REJECT` — гонит на TCP (важно для Vision/детекта).
- **remnawave include-proxies**: боевые хосты подставляет панель, в файле только служебный `DIRECT`.
- **TUN** (`stack: mixed`) + **sniffer** (SNI/Host для доменных правил).

Расширять под себя: добавить группы (YouTube/Discord/игры), `PROCESS-NAME`-правила для игр/лаунчеров,
push мимо VPN (Apple `17.0.0.0/8`, FCM `5228-5230`), свои rule-providers.

## Грабли

1. **Reality без `client-fingerprint` не поднимется** (`REALITY is based on uTLS, please set a client-fingerprint`).
2. **`global-client-fingerprint` выпилен в v1.19.27** — только per-proxy.
3. **DNS-петля** — `default-nameserver` только IP; хост прокси-сервера через `proxy-server-nameserver`.
4. **fake-ip** требует полного перехвата трафика.
5. **rule-providers**: не мешать типы в `behavior: domain`-файле (issue #1400).
6. **geodata** качается с GitHub при старте — из РФ/CN лучше зеркало через `geox-url` (эталон использует jsdelivr).