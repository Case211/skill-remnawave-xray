# Remnawave / Xray-Reality / Caddy-selfsteal / mihomo — Gemini context

Справочник по узкому VPN-стеку. Основной контент — в `skills/remnawave-xray/`. Сверяйся с файлами, не по памяти.

Область: Remnawave (панель/нода/подписки), Xray-core (VLESS+Reality+XTLS-Vision, транспорты, протоколы, Hysteria 2),
Caddy selfsteal-заглушка, mihomo/Clash.Meta клиент.

Куда смотреть:
- Обзор/инварианты/версии — `skills/remnawave-xray/SKILL.md`
- Reality/Vision — `skills/remnawave-xray/reference/xray-reality.md`
- Транспорты (xhttp/ws/grpc/mkcp/hysteria) — `skills/remnawave-xray/reference/transports.md`
- Протоколы (vmess/trojan/ss/wireguard/HY2, статус TUIC/AnyTLS) — `skills/remnawave-xray/reference/protocols.md`
- Caddy selfsteal — `skills/remnawave-xray/reference/caddy-selfsteal.md`
- mihomo — `skills/remnawave-xray/reference/mihomo.md` · Панель — `skills/remnawave-xray/reference/remnawave.md`
- Генерация — `skills/remnawave-xray/generators.md` · Диагностика — `skills/remnawave-xray/diagnostics.md` · Примеры — `skills/remnawave-xray/examples/`

Инварианты: порт 443; `target` → localhost Caddy, `serverNames == домен` (DNS-only, НЕ Cloudflare); flow только
`xtls-rprx-vision` (raw); `client-fingerprint` обязателен; `network: "raw"` (не tcp).
Версии: Remnawave 2.8.0 · Xray-core v26.6.27 · Caddy 2.11.4 · mihomo 1.19.27.