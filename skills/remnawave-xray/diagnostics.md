# Диагностика: симптом → причина → фикс

## Reality / Xray (ошибки в логах)

| Сообщение / симптом | Причина | Фикс |
|---|---|---|
| `REALITY: processed invalid connection` (клиент) + `received real certificate` | AuthKey не прошёл: неверный `password`/pbk или `shortId`, либо реальный MITM | pbk = `xray x25519 -i "<privateKey>"`; сверить shortId; проверить что нет CDN перед target |
| `processed invalid connection ... failed to read client hello` (сервер) | сканер/пробер без валидного ClientHello | фоновый шум; тревога — если от твоих юзеров с одного ISP (возможен DPI) |
| `please fill in a valid value for "target"` | `target`/`dest` не парсится | формат `host:port` / порт / unix-путь |
| `invalid PROXY protocol version, "xver" only accepts 0, 1, 2` | `xver` вне диапазона | 0/1/2 |
| `invalid "privateKey"` / `invalid "password"` | длина != 32 байта после base64 | перегенерировать `xray x25519`, не путать Private/Public |
| `non-empty "serverNames", please use "serverName"` | вставили серверные (мн.ч.) поля в клиент | на клиенте единственное число: `serverName`/`shortId` |
| `too long "shortIds[i]"` / `invalid "shortIds[i]"` | >16 hex / нечётная длина / не-hex | `openssl rand -hex 8` |
| `unknown "fingerprint"` / `unsafe` | опечатка/запрещённое значение | `chrome`/`firefox`/`randomized` |
| `does not support TLS 1.3, REALITY handshake cannot establish` | fingerprint не даёт TLS1.3 key-share | современный fingerprint |
| warning `Choosing apple, icloud... may get your IP blocked` | `apple`/`icloud` в serverNames | сменить target/serverNames |
| `REALITY is based on uTLS, please set a client-fingerprint` (mihomo) | нет `client-fingerprint` при `reality-opts` | добавить `client-fingerprint: chrome` |

## Нода не подключается к панели

| Симптом | Причина | Фикс |
|---|---|---|
| нода `disconnected` в панели, Xray не стартует | панель не достучалась (панель→нода) | firewall ноды: открыть `NODE_PORT` для IP панели; проверить `docker logs remnanode` |
| mTLS/JWT ошибки в логах ноды | битый/чужой `SECRET_KEY` | пересоздать: панель CLI → «Get SECRET_KEY for Node», вставить в `.env` ноды |
| нода поднялась, юзеры не коннектятся | норма, что `clients: []` в профиле — панель инжектит; проверь что нода активна и Host привязан к инбаунду | Squad включает инбаунд, Host выбирает его |
| рассинхрон времени → handshake fail | часы ноды/клиента разъехались | NTP на ноде и клиенте |

## Caddy

| Симптом | Причина | Фикс |
|---|---|---|
| Caddy-контейнер не стартует | порт `<SELF_STEAL_PORT>` занят или синтаксис Caddyfile | `docker logs caddy`; `ss -tlnp`; `caddy validate` |
| Reality-заглушка отдаёт 502 / пусто | `target` Xray не совпал с портом Caddy, Caddy не поднялся | `SELF_STEAL_PORT` один и тот же в Xray `target` и Caddy `https_port` |
| `400 Bad Request` на `:80`, `client_ip=127.0.0.1` | `servers { }` без адреса → proxy_protocol протёк на 80 | `servers 127.0.0.1:<PORT> { ... }` (адресный скоуп) |
| ACME не выпускает серт | 80 закрыт / TLS-ALPN на занятом 443 / домен под Cloudflare / rate-limit | открыть 80; `disable_tlsalpn_challenge`; домен DNS-only; не пересоздавать серт в цикле |
| в логах реальный IP = 127.0.0.1 | `xver:1`, но нет `proxy_protocol` враппера (или наоборот) | согласовать `xver` ↔ `listener_wrappers.proxy_protocol` |

## mihomo (клиент)

| Симптом | Причина | Фикс |
|---|---|---|
| Reality-прокси не поднимается | нет `client-fingerprint` | добавить per-proxy; `global-client-fingerprint` мёртв с 1.19.27 |
| нет DNS / всё отваливается | DNS-петля (домен прокси через прокси) или `default-nameserver` с доменом | `default-nameserver` только IP; хост прокси → `proxy-server-nameserver` |
| часть приложений без интернета | `fake-ip` без полного перехвата (не весь трафик в TUN) | TUN/системный прокси на весь трафик, либо в `fake-ip-filter` |
| старт падает на geodata | GitHub недоступен из региона | `geox-url` на зеркало (jsdelivr) |
| RU-домены идут через прокси (не DIRECT) | сломан rule-provider `behavior: domain` (примешан IP-CIDR) | не мешать типы в domain-файле (issue #1400) |

## Reality палится (работает, но банят IP)

Проверить по `reference/xray-reality.md` → анти-пробинг чек-лист: порт 443; разумный `target` (TLS1.3+H2, свой ASN, не
мега-бренд); `xtls-rprx-vision`; актуальный fingerprint; `show:false`; не сотни юзеров на один IP; NTP.
Иран/жёсткий DPI: репутация IP, симметрия трафика, объём — см. раздел в `reference/xray-reality.md`.

## Диагностические команды

```
# Xray
xray run -test -c /path/config.json        # валидация конфига
xray tls ping <serverName>                 # TLS1.3 / X25519MLKEM768 / серт target
docker exec -it remnanode cli              # --dump-config (холодный конфиг)
docker exec remnanode xlogs                # логи Xray ноды

# Порты / сеть
ss -tlnp                                   # кто слушает 443/80/9443/NODE_PORT
ss -tlnp | grep -E ':(443|80|9443)'
curl -I http://<domain>                    # редирект на HTTPS (Caddy :80)
openssl s_client -connect <ip>:443 -servername <domain> </dev/null 2>/dev/null | openssl x509 -noout -subject -dates
                                           # какой серт отдаёт 443 (при провале Reality-auth — серт заглушки)

# Caddy
docker logs caddy --tail 100
caddy validate --config /etc/caddy/Caddyfile

# Нода / панель
docker logs remnanode --tail 100 -t
docker exec -it remnawave pm2 monit        # состояние api/scheduler/processor
curl -f http://127.0.0.1:3001/health       # health панели
```

Параметры и их валидация → `reference/xray-reality.md`. Согласованность → `generators.md`.