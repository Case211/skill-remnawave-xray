# Caddy: selfsteal-заглушка

Caddy **2.11.4**. Роль — отдавать реальный сайт-заглушку по твоему домену, куда Xray Reality
форвардит непрошедший авторизацию трафик (`target` = локальный Caddy). Для внешнего наблюдателя —
обычный сайт с настоящим ACME-сертом. Синтаксис сверен с caddyserver.com/docs.

`proxy_protocol` встроен в ядро **с v2.7.0** (отдельная сборка не нужна). `layer4` (mholt/caddy-l4) —
**НЕ core**, для selfsteal не требуется.

## Карта портов (Caddy)

| Порт | Bind | Назначение |
|---|---|---|
| `80` | `0.0.0.0` | ACME HTTP-01 challenge + редирект на HTTPS. Caddy держит сам — работает, даже когда 443 занят Xray. |
| `<SELF_STEAL_PORT>` (9443) | `127.0.0.1` | HTTPS-заглушка (реальный сайт) за Reality `target`. |
| тот же порт | — | catch-all блок для запросов без валидного SNI (сканеры по IP). |

## Ключевые решения (из официальной доки)

- **`servers` СО скоупом по адресу** — `servers 127.0.0.1:<PORT> { ... }`, НЕ пустой `servers { }`.
  Пустой применяет `listener_wrappers` ко ВСЕМ серверам, включая ACME/redirect на `:80` → `proxy_protocol`
  ждёт заголовок, которого на 80 нет → `400 Bad Request` / `client_ip = 127.0.0.1` (issue #5602, #6390).
  Адрес в `servers` должен **точно** совпадать с эффективным bind сайта.
- **Порядок в `listener_wrappers`: `proxy_protocol` ДО `tls`.** PROXY-заголовок идёт первым, до TLS ClientHello;
  если `tls` первый — он попытается распарсить заголовок как handshake и сломается. `tls` — no-op маркер, но раз
  `listener_wrappers` объявлен вручную, его нужно дописать явно (иначе TLS-терминации не будет вовсе).
- **`https_port` — «internal only»**: влияет на внутреннюю логику/дефолтный порт для `https://`, реальный listen
  задаёт адрес сайта/`bind`.
- **ACME: только HTTP-01 на `:80`.** TLS-ALPN-01 требует реальный 443 (занят Xray) → отключить:
  `tls { issuer acme { disable_tlsalpn_challenge } }`. DNS-01 — если не хочешь открывать 80 (нужны креды DNS-провайдера).
- `xver: 1` в Reality → нужен `proxy_protocol { allow 127.0.0.1/32 }`, иначе Caddy видит `127.0.0.1` вместо
  реального IP пробера. `xver: 0` → убрать `proxy_protocol` из враппера, иначе Caddy ждёт несуществующий заголовок.

## Эталонный Caddyfile (адресный скоуп + отключённый TLS-ALPN)

```caddyfile
{
	email <ACME_EMAIL>
	https_port {$SELF_STEAL_PORT:9443}

	# скоуп ТОЛЬКО на loopback-порт заглушки — :80 (ACME) не трогаем
	servers 127.0.0.1:{$SELF_STEAL_PORT:9443} {
		listener_wrappers {
			proxy_protocol {
				allow 127.0.0.1/32
				timeout 5s
			}
			tls
		}
		protocols h1 h2
	}
	auto_https disable_redirects
	admin off
}

# реальный сайт-заглушка — настоящий ACME-серт через HTTP-01 (:80)
{$SELF_STEAL_DOMAIN}:{$SELF_STEAL_PORT:9443} {
	bind 127.0.0.1
	tls {
		issuer acme { disable_tlsalpn_challenge }
	}
	root * {$HTML_DIR:/var/www/html}
	encode zstd gzip
	header -Server
	try_files {path} /index.html
	file_server
}

# редирект + ACME challenge на :80 (Caddy держит сам)
http://{$SELF_STEAL_DOMAIN} {
	bind 0.0.0.0
	redir https://{$SELF_STEAL_DOMAIN}{uri} permanent
}

# catch-all: запросы без валидного SNI (сканеры по IP) — пустой 204, самоподписанный
:{$SELF_STEAL_PORT:9443} {
	tls internal
	respond 204
	log off
}
```

Вариант из `DigneZzZ/selfsteal.sh` (Caddy 2.11.4) использует `servers { }` без адреса, компенсируя
`default_bind 127.0.0.1` — рабочее, но официал рекомендует адресный скоуп выше как более надёжный.

## docker-compose (host-network)

```yaml
services:
  caddy:
    image: caddy:2.11.4
    container_name: caddy-selfsteal
    restart: unless-stopped
    network_mode: "host"          # обязательно: PROXY-protocol + точные порты
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ${HTML_DIR}:/var/www/html
      - ./logs:/var/log/caddy
      - caddy_data:/data
      - caddy_config:/config
    env_file: [.env]
volumes: { caddy_data: {}, caddy_config: {} }
```

## Директивы (шпаргалка)

`file_server [browse]` (index def `index.html index.txt`) · `respond 204` / `respond "text" 403` ·
`redir <to> permanent|temporary` (def temporary/302) · `encode zstd gzip` (def zstd>gzip, brotli только с диска) ·
`header -Server` (удалить) / `header +X-Foo bar` · `root * /path` (с 2.8.0 `*` необязателен) ·
`try_files {path} /index.html` · `bind 127.0.0.1` (без порта) · `tls internal|<email>|<cert> <key>`.

## Грабли

1. **Домен под Cloudflare (оранжевое облако) — ЛОМАЕТ и ACME, и Reality.** CF терминирует TLS, ключа Reality нет.
   Домен selfsteal — строго **DNS-only** (серое облако).
2. **Порт 80 закрыт в firewall** → ACME HTTP-01 не проходит. Частая ошибка: открыли только 443.
3. **`SELF_STEAL_PORT` не совпал** между Caddyfile (`https_port`) и Xray `target` → 502/заглушка недоступна.
4. **SNI-mismatch**: `SELF_STEAL_DOMAIN` в Caddy != `serverNames` в Reality → клиент не подключается / заглушка не та.
5. **Let's Encrypt rate-limits**: 5 дубль-сертов/7 дней, 50 сертов/домен/7 дней, 5 провалов авторизации/час.
   Не пересоздавать серт бездумно при отладке (Caddy сам уходит в staging при провале).
6. **`servers` без адреса** ломает `:80` (см. выше) — держать адресный скоуп.
7. **Не `network_mode: host`** → через bridge+NAT ломается PROXY-protocol и разъезжаются порты.

Как это стыкуется с Xray → `architecture.md`. Reality `target`/`xver` → `xray-reality.md`.