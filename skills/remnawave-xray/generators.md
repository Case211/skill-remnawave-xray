# Генератор конфигов

Режим: взять готовый эталон из `examples/`, подставить параметры вместо плейсхолдеров, прогнать
чек-лист согласованности, провалидировать. Эталоны обезличены — плейсхолдеры в угловых скобках.

## Готовые шаблоны (examples/)

| Файл | Что это | Куда |
|---|---|---|
| `examples/xray-selfsteal-node.json` | VLESS+Reality inbound (raw, target→Caddy) + routing | Config Profile ноды |
| `examples/xray-cdn-bridge.json` | CDN-мост: WS+XHTTP inbounds на localhost → Reality outbound на выход | Config Profile CDN-ноды |
| `examples/xray-client-ru-routing.json` | клиентский Xray: РФ напрямую, остальное в proxy, socks/http | десктоп-клиент |
| `examples/xray-balancer-leastload.json` | подписочный XRAY_JSON с `injectHosts` + `leastLoad` balancer | XRAY_JSON template (панель) |
| `examples/xray-balancer-random.json` | то же с `random` balancer (CDN-пул) | XRAY_JSON template (панель) |
| `examples/mihomo-example.yaml` | клиентский mihomo: TUN, fake-ip, РФ-роутинг (публичные rule-sets) | MIHOMO template (панель) |
| `examples/subscription-response-rules.json` | Response Rules (SRR) по User-Agent | панель: Subscription → Response Rules |

## Плейсхолдеры (что подставить)

| Плейсхолдер | Значение |
|---|---|
| `<SELF_STEAL_DOMAIN>` / `<DE_NODE_DOMAIN>` | твой домен-заглушка, DNS-only, резолвится на IP ноды |
| `<SELF_STEAL_PORT>` | локальный HTTPS-порт Caddy (дефолт 9443) |
| `<REALITY_PRIVATE_KEY>` | `xray x25519` → строка Private key (в inbound профиля) |
| `<REALITY_PUBLIC_KEY>` | `xray x25519 -i "<privkey>"` → Password/PublicKey (outbound/подписка; панель делает сама из privateKey) |
| `<SHORT_ID>` | `openssl rand -hex 8` (или `""`) |
| `<CLIENT_UUID>` | `xray uuid` |
| `<CDN_FRONT_HOST>` / `<CDN_DOMAIN>` | домен CDN-фронта (для XHTTP host) |
| `<ACME_EMAIL>` / `<HTML_DIR>` | email для ACME / папка статики заглушки |

## Команды генерации

```
xray x25519                        # privateKey (сервер) + publicKey
xray x25519 -i "<privateKey>"      # publicKey из приватного (для клиента/подписки)
xray uuid                          # UUID клиента (xray uuid -i "строка" — детерминированный UUIDv5)
xray mldsa65                       # seed(сервер) + verify(клиент) — post-quantum, опц.
openssl rand -hex 8                # shortId (16 hex, чётная длина)
xray vlessenc                      # decryption/encryption для VLESS Encryption (опц.)
```

В Remnawave x25519-пару генерит сама панель (Keygen); руками ключи обычно не трогаешь — pbk выводится из
privateKey профиля автоматически при сборке подписки.

## Автопроверка

Вместо ручного прогона чек-листа ниже — исполняемый валидатор (stdlib Python, без зависимостей):

```
python validate.py <config.json>              # только Xray Config Profile
python validate.py <config.json> Caddyfile    # + кросс-чек target↔порт, xver↔proxy_protocol
```

Проверяет пункты 1–8 из чек-листа: порт 443, security×network, flow только на raw, ключи 32 байта,
shortIds (hex/чётность/≤16), serverNames (apple/icloud), xver 0/1/2, allowInsecure, согласование с Caddy.
Плейсхолдеры `<...>` не считает ошибкой. Код выхода 1 при ошибках. Ручной чек-лист — ниже, как справка.

## Чек-лист согласованности (нарушишь — не работает)

1. **Домен один и тот же**: `serverNames` (inbound) == `serverName`/SNI (outbound/Host) == `SELF_STEAL_DOMAIN`
   (Caddy) == домен, A-записью указывающий на IP ноды. DNS-only (не Cloudflare-proxy).
2. **target ↔ Caddy порт**: `target: "127.0.0.1:<SELF_STEAL_PORT>"` (inbound) == `https_port` (Caddy) == порт
   catch-all и site-блока.
3. **Ключи — пара**: `password`/pbk (клиент) = `xray x25519 -i "<privateKey сервера>"`. Разные ключи → `processed
   invalid connection`.
4. **shortId** клиента ∈ `shortIds` сервера (или обе `""`). Длина чётная, ≤16 hex.
5. **flow совпадает**: `xtls-rprx-vision` на inbound-clients и outbound-users, только `network: raw`.
6. **fingerprint задан на клиенте** (`client-fingerprint` в mihomo / `fingerprint` в xray-outbound). Reality без него не встанет.
7. **xver ↔ proxy_protocol**: `xver: 1` → Caddy `listener_wrappers.proxy_protocol`; `xver: 0` → без враппера.
8. **Порт 443** для боевого inbound (не-443 → warning ядра + бан).

## Мини-рецепты

**Selfsteal-нода:** `examples/xray-selfsteal-node.json` в Config Profile → задать `<SELF_STEAL_PORT>`, `<DOMAIN>`,
`privateKey` (панель). Рядом Caddy (`reference/caddy-selfsteal.md`) с тем же портом/доменом. Host: SNI пусто
(наследует из инбаунда), `fingerprint`, address=домен.

**CDN-мост:** `examples/xray-cdn-bridge.json` — WS/XHTTP inbounds слушают `127.0.0.1` за реверс-прокси (nginx/Caddy →
CDN), `host` = `<CDN_FRONT_HOST>`, `path` маскируется под легитимные API/Next.js-пути. Outbound `ToGermany` —
Reality на выходную ноду (`serverName` = её домен, `password` = её pubkey). Routing гонит все inbound-tag → выход.

**Балансировщик в подписке:** `examples/xray-balancer-*.json` как XRAY_JSON template. `remnawave.injectHosts.selector`
подтягивает скрытые (`isHidden`) хосты по `remarkRegex` (напр. `^BAL-`/`^CDN-`), `burstObservatory` пингует,
`leastLoad`/`random` balancer раскидывает. Скрытые хосты создать в панели с нужным префиксом remark.

**Клиент/mihomo:** `examples/mihomo-example.yaml` или `examples/xray-client-ru-routing.json` — обычно это subscription template в
панели (не руками), плейсхолдеры хостов заполняет панель. Для standalone — подставить свои прокси.

Проверка результата → `diagnostics.md` (валидация конфига, тест хендшейка).