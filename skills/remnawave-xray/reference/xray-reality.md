# Xray-core: VLESS + Reality + XTLS-Vision

Xray-core **v26.6.27** (CalVer `vYY.M.D`). Имена полей и валидация сверены с официальной
докой `xtls.github.io` (en/ru/zh совпадают) и исходниками `infra/conf/transport_internet.go`.
Один struct обслуживает inbound и outbound — роль определяется наличием `target`/`dest`.

Полный дамп офиц. доки для точечной сверки: https://xtls.github.io/llms-full.txt (642 КБ, first-party).

## Что важно не тащить из старых туториалов

- **`network: "tcp"` переименован в `"raw"`** (релиз v24.9.30). `tcp.html` в доке — редирект на RAW.
  В хранимых конфигах встречаются оба; клиентская `vless://`-ссылка нормализует обратно в `type=tcp`.
- **`dest` -> `target`**, **`publicKey` -> `password`** — переименованы, старые имена оставлены алиасами.
  `password` на клиенте — это x25519 public key сервера, просто «не для публикации» по модели Reality.
- **`allowInsecure` УДАЛЁН** (v26.2.6) -> замена `pinnedPeerCertSha256` (+ `verifyPeerCertByName` для SNI-проверки).
- **Legacy XTLS-flow мертвы** (`xtls-rprx-direct/-splice/-origin`) -> только `xtls-rprx-vision`.
- **Post-quantum (опц., обратно совместимо):** `mldsa65Seed`/`mldsa65Verify` (ML-DSA-65 подпись; **условие:
  сертификат `target` должен быть > 3500 байт**), гибридный обмен ключами X25519MLKEM768 (uTLS «как Chrome»).
- Ядро выдаёт warning на `apple`/`icloud` в `serverNames` и на не-443 порт (по опыту RPRX — «легко ведёт к бану IP»).

## Матрица `security` x `network` (жёсткое ограничение, проверять при валидации)

| security | Совместимые транспорты |
|---|---|
| `reality` | **только** `raw`, `xhttp`, `grpc` |
| `tls` | все (`raw`, `xhttp`, `mkcp`, `grpc`, `websocket`, `httpupgrade`, `hysteria`) |

`flow: xtls-rprx-vision` — **только `raw`**. Reality поверх XHTTP/gRPC -> `flow` НЕ указывать.

## Inbound (сервер) — `streamSettings.realitySettings`

| Поле | Обяз. | Значение / валидация |
|---|---|---|
| `target` (`dest`) | да | `host:port` / голый порт (host=localhost) / unix-путь. Оба заданы -> побеждает `target`. selfsteal -> `127.0.0.1:<SELF_STEAL_PORT>`. Роль сервера определяется наличием этого поля — на клиенте не заполнять. |
| `serverNames` | да | список допустимых SNI. Пустой список -> ошибка. `*` не поддерживается, но `""` допустим (принимать без SNI). == `SELF_STEAL_DOMAIN`. |
| `privateKey` | да | x25519 (`xray x25519`), base64 RawURLEncoding, ровно 32 байта. Хранится внутри Config Profile панели, наружу не уходит. |
| `shortIds` | да | список hex <=16 симв, **чётной длины**; `""` допустим. |
| `xver` | нет | PROXY-protocol на форвард к target: **0/1/2**. selfsteal обычно 1. |
| `minClientVer` / `maxClientVer` | нет | `"x.y.z"`, каждый компонент 0-255. |
| `maxTimeDiff` | нет | допустимый разброс часов, мс (обычно 0 или ~60000). |
| `mldsa65Seed` | нет, only server | seed ML-DSA-65 (`xray mldsa65`), 32 байта, != privateKey. **Нужен cert target > 3500 байт.** |
| `limitFallbackUpload` / `limitFallbackDownload` | нет | `{afterBytes, bytesPerSec, burstBytesPerSec}` — троттлинг непрошедших авторизацию. Офиц. предупреждение: сам лимит — тоже отпечаток. |
| `show` | нет (false) | отладка. **В проде `false`.** |

## Outbound (клиент) — `streamSettings.realitySettings`

| Поле | Обяз. | Валидация |
|---|---|---|
| `serverName` | да | **единственное число** (мн. -> ошибка `please use "serverName"`). Можно IP -> тогда сервер должен иметь `""` в serverNames. |
| `fingerprint` | да (deflt `chrome`) | uTLS-профиль. `unsafe`/`hellogolang` запрещены (Reality завязан на uTLS). |
| `password` (`publicKey`) | да | серверный pubkey = `xray x25519 -i "<privateKey>"`, 32 байта. |
| `shortId` | да | **единственное число**, один из серверных shortIds. |
| `spiderX` | нет (deflt `/`) | путь имитации краулера, начинается с `/`, поддерживает query (ниже). Рекомендуется разный на клиента. |
| `mldsa65Verify` | нет | pubkey проверки ML-DSA-65, 1952 байта. |

### `spiderX` query (`min-max` или число)

`p` padding / `c` concurrency / `t` times / `i` interval(мс) / `r` return-delay(мс).
Пример: `/gallery?p=100-200&c=2-4&t=3-5&i=10-25&r=5-15`

### `fingerprint`

`chrome` `firefox` `safari` `ios` `android` `edge` `360` `qq` `random` `randomized` `randomizednoalpn`.
- `random` — выбирает готовый из пула; `randomized` — генерирует новый каждый раз (совместим с Vision).
- Анекдот сообщества: статичный `chrome` на shared-ноде иногда ловит ISP-шейпинг по fingerprint -> `randomized` спасает.

## Требования к `target`/`serverNames`

Минимум (README XTLS/REALITY): сайт вне блокировок юрисдикции, **TLS 1.3 + HTTP/2**, без редиректа на другой
домен (apex->www ок). Бонус: IP target близок по гео/ASN; OCSP stapling.

**Почему selfsteal лучше «чужого сайта»:** свой домен + свой ACME-серт + свой реальный сайт убирает
несовпадение IP/ASN/SNI. Чужой мега-бренд (`apple.com` с дешёвого VPS) палится репутационно без взлома крипты.
Официальное предупреждение: непрошедший авторизацию трафик ядро **напрямую форвардит** на `target` — если target
за CDN (Cloudflare), сервер становится форвардером чужого CDN. Рекомендация: воровать серт у сайта **того же ASN**,
либо ставить SNI-фильтр перед Xray.

**Иран (Discussion #3269):** скорость бана растёт с объёмом трафика (нода 200+ юзеров/CPU 100% — бан за 2 часа);
графлист по репутации IP; популярный SNI банят быстрее; несовпадение reverse-DNS и SNI — сигнал; симметричный
битрейт — признак VPN; часть операторов резала TLS 1.3. Помогало: реальный сайт на 443, локальный непопулярный домен.

## flow `xtls-rprx-vision`

- Совпадает на сервере (`clients[].flow`) и клиенте (`users[].flow`). Только поверх `raw` + tls/reality.
- `xtls-rprx-vision-udp443` — то же, но **не** перехватывает UDP:443 (не ломает нативный QUIC приложения).
- **Splice** (Linux): при TCP+TLS1.3 ядро форвардит напрямую мимо памяти Xray -> почти нативная скорость,
  убирает TLS-in-TLS сигнатуру. Статистика скорости при Splice отображается с задержкой.
- `decryption`/`encryption` = `"none"` (Vision полагается на внешний Reality/TLS-слой).

## Анти-пробинг чек-лист

1. Разумный `target`: TLS1.3+H2, правдоподобный IP/ASN, не мега-бренд, в идеале реальный сайт (selfsteal).
2. Порт **443**. 3. `xtls-rprx-vision` на raw. 4. Актуальный uTLS fingerprint (или `randomized`).
5. Никаких `allowInsecure`-схем (их и нет). 6. `show: false`. 7. Не сваливать сотни юзеров на один IP.
8. NTP на клиенте и сервере (anti-replay метка времени в ClientHello).

## Reality + CDN — это НЕ selfsteal (не путать)

Reality/XHTTP через CDN — **другой инбаунд** (XHTTP-транспорт, без Vision-flow), где домен как раз проксируется
CDN. Для классического selfsteal своего домена Cloudflare-proxy на этом домене НЕДОПУСТИМ (ломает ACME и Reality).
Боевой документ использует обе техники раздельно: selfsteal-нода (Reality на 443) + отдельный CDN-мост (XHTTP+WS
на localhost за реверс-прокси) — см. `../examples/xray-cdn-bridge.json` и `../generators.md`.

## Эталон (обезличено, из боевого профиля)

Полные файлы: `../examples/xray-selfsteal-node.json`, `../examples/xray-cdn-bridge.json`.

Selfsteal inbound (суть):
```json
{ "tag": "Germany W", "port": 443, "listen": "0.0.0.0", "protocol": "vless",
  "settings": { "clients": [], "decryption": "none" },
  "sniffing": { "enabled": true, "destOverride": ["http","tls","quic"] },
  "streamSettings": { "network": "raw", "security": "reality",
    "realitySettings": { "show": false, "xver": 0, "target": "127.0.0.1:9443",
      "shortIds": [""], "privateKey": "<REALITY_PRIVATE_KEY>", "serverNames": ["<DE_NODE_DOMAIN>"] } } }
```
`clients: []` в inbound — норма: Remnawave инжектит реальных юзеров динамически (см. `remnawave.md`).

## Команды

```
xray x25519                       # Private key + Password(PublicKey)
xray x25519 -i "<server privkey>" # publicKey для клиента
xray mldsa65                      # seed + verify (post-quantum, опц.)
xray uuid [-i "строка"]           # UUIDv4 или UUIDv5 из строки
xray vlessenc                     # пара decryption/encryption для VLESS Encryption
xray tls ping <domain>            # проверка TLS1.3 / X25519MLKEM768 / серта target
openssl rand -hex 8               # shortId (16 hex, чётная длина)
xray run -test -c config.json     # проверка конфига
```

Шаблоны генерации -> `../generators.md`. Разбор ошибок хендшейка -> `../diagnostics.md`.