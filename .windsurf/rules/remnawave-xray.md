---
trigger: model_decision
description: Remnawave VPN stack — Xray Reality/Vision, Caddy selfsteal, mihomo. Reference, config generation, diagnostics.
---

Справочник по стеку **Remnawave / Xray-Reality / Caddy-selfsteal / mihomo**. Контент — в `skills/remnawave-xray/`,
сверяйся с файлами, не по памяти:

- Обзор/инварианты — `skills/remnawave-xray/SKILL.md`
- Reality/Vision — `skills/remnawave-xray/reference/xray-reality.md`
- Транспорты — `skills/remnawave-xray/reference/transports.md` · Протоколы — `skills/remnawave-xray/reference/protocols.md`
- Caddy — `skills/remnawave-xray/reference/caddy-selfsteal.md` · mihomo — `skills/remnawave-xray/reference/mihomo.md` · Панель — `skills/remnawave-xray/reference/remnawave.md`
- Генерация — `skills/remnawave-xray/generators.md` · Диагностика — `skills/remnawave-xray/diagnostics.md` · Примеры — `skills/remnawave-xray/examples/`

Инварианты: порт 443; `target` → localhost Caddy, `serverNames == домен` (DNS-only, не Cloudflare); flow только
`xtls-rprx-vision` (raw); `client-fingerprint` обязателен; `network: "raw"` (не tcp).