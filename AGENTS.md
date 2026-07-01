# Remnawave / Xray-Reality / Caddy-selfsteal / mihomo — agent guide

Экспертный справочник по узкому VPN-стеку. Основной контент — в `skills/remnawave-xray/` (формат
Claude Code skill, но это обычный markdown, читаемый любым агентом). Этот `AGENTS.md` — точка входа
для Codex и других инструментов, читающих стандарт AGENTS.md.

## Когда применять

Работа с: **Remnawave** (панель/нода/подписки), **Xray-core** (VLESS+Reality+XTLS-Vision, транспорты,
протоколы, Hysteria 2), **Caddy** selfsteal-заглушкой, **mihomo/Clash.Meta** клиентом.

## Куда смотреть — сверяйся с файлами, не отвечай по памяти

| Тема | Файл |
|---|---|
| Обзор, инварианты, карта портов, версии | `skills/remnawave-xray/SKILL.md` |
| Как устроена selfsteal-нода (порты, потоки, xver) | `skills/remnawave-xray/reference/architecture.md` |
| Reality/Vision параметры, post-quantum, анти-пробинг | `skills/remnawave-xray/reference/xray-reality.md` |
| Транспорты: xhttp/ws/grpc/httpupgrade/mkcp/hysteria | `skills/remnawave-xray/reference/transports.md` |
| Протоколы: vmess/trojan/ss/wireguard/VLESS-Enc, HY2, статус TUIC/AnyTLS | `skills/remnawave-xray/reference/protocols.md` |
| Caddy selfsteal (Caddyfile, ACME, proxy_protocol) | `skills/remnawave-xray/reference/caddy-selfsteal.md` |
| mihomo клиент (DNS/rules/sniffer/TUN) | `skills/remnawave-xray/reference/mihomo.md` |
| Панель Remnawave (Profile→Inbound→Host→Squad) | `skills/remnawave-xray/reference/remnawave.md` |
| Генерация конфигов + команды ключей | `skills/remnawave-xray/generators.md` |
| Диагностика: симптом → причина → фикс | `skills/remnawave-xray/diagnostics.md` |
| Обезличенные конфиги-эталоны | `skills/remnawave-xray/examples/` |

## Железные инварианты (нарушишь — не работает или палится)

- Порт **443**; `realitySettings.target` → локальный Caddy, `serverNames == SELF_STEAL_DOMAIN`.
- Домен selfsteal — **DNS-only** (НЕ под Cloudflare-proxy — иначе ломается ACME и Reality).
- flow только `xtls-rprx-vision` (поверх `raw`); на клиенте **`client-fingerprint` обязателен**.
- `network: "raw"` (не `tcp`); официальные имена `target`/`password` (не dest/publicKey).
- Ключи: privateKey/publicKey 32 байта; `pubkey = xray x25519 -i "<privateKey>"`.

Версии (сверять перед деплоем): Remnawave **2.8.0** · Xray-core **v26.6.27** · Caddy **2.11.4** · mihomo **1.19.27**.
