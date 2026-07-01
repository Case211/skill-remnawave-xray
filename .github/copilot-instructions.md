# Copilot instructions — Remnawave / Xray / Caddy / mihomo stack

Этот репозиторий — экспертный справочник по узкому VPN-стеку. При работе с Remnawave, Xray-core
(VLESS+Reality+Vision, транспорты, Hysteria 2), Caddy selfsteal, mihomo/Clash.Meta — сверяйся с
`skills/remnawave-xray/`, не отвечай по памяти:

- Обзор/инварианты/версии — `skills/remnawave-xray/SKILL.md`
- Reality/Vision — `skills/remnawave-xray/reference/xray-reality.md`
- Транспорты/протоколы — `skills/remnawave-xray/reference/transports.md`, `skills/remnawave-xray/reference/protocols.md`
- Caddy — `skills/remnawave-xray/reference/caddy-selfsteal.md` · mihomo — `skills/remnawave-xray/reference/mihomo.md` · Панель — `skills/remnawave-xray/reference/remnawave.md`
- Генерация — `skills/remnawave-xray/generators.md` · Диагностика — `skills/remnawave-xray/diagnostics.md` · Примеры — `skills/remnawave-xray/examples/`

Инварианты: порт 443; `target` → localhost Caddy, `serverNames == домен` (DNS-only, не Cloudflare); flow только
`xtls-rprx-vision` (raw); `client-fingerprint` обязателен; `network: "raw"` (не tcp). Версии: Remnawave 2.8.0 · Xray v26.6.27 · Caddy 2.11.4 · mihomo 1.19.27.