# remnawave-xray

**English** · [Русский](README.md)

> **Claude Code / agent skill** for the **Remnawave + Xray (Reality/Vision) + Caddy selfsteal + mihomo** stack.
> Stack reference, config generator, and symptom → cause → fix diagnostics — sourced from official docs and source code, not blog posts.

## What it is

An agent skill that keeps the fiddly, fast-moving specifics of one narrow stack in a single, verified place:

- **Remnawave** — orchestrator panel (Config Profile → Inbound → Host → Squad), node (RemnaNode = Xray-core), subscriptions.
- **Xray-core** — VLESS + Reality + XTLS-Vision, transports (raw/xhttp/ws/grpc/httpupgrade/mkcp/hysteria), protocols, Hysteria 2.
- **Caddy** — selfsteal decoy (a real site behind the Reality `target`, ACME, `proxy_protocol`).
- **mihomo (Clash.Meta)** — client config: DNS/fake-ip, rules, sniffer, TUN.

Three modes: **reference** (answer from the files, not from memory), **generator** (template → placeholders → consistency checklist + an executable `validate.py`), **diagnostics** (symptom → cause → fix + commands).

## ⚠️ Disclaimer

This material is **educational**. Reality/selfsteal/Hysteria are privacy and censorship-circumvention technologies; use them within the law of your jurisdiction. The configs under `examples/` are **anonymized** (placeholders instead of domains/keys, generic paths) — they will not run as-is, they are templates. Verify versions and "fresh" fields (e.g. Hysteria 2) against current releases before shipping to production.

## Structure

```
.claude-plugin/
  marketplace.json           marketplace manifest
  plugin.json                plugin manifest
skills/remnawave-xray/       ← the skill itself:
  SKILL.md                   router: invariants, port map, versions, routing
  reference/                 architecture · xray-reality · caddy-selfsteal · mihomo · remnawave · transports · protocols · routing
  generators.md              templates + key commands + consistency checklist
  validate.py                executable config consistency check (stdlib)
  diagnostics.md             symptom → cause → fix + diagnostic commands
  examples/                  anonymized reference configs (Xray/Caddy/mihomo/subscription)
tools/
  sync-check.py              verifies the cross-tool entry points have not drifted from the canonical skill
```

## Installation

**Claude Code — via marketplace:**

```
/plugin marketplace add Case211/skill-remnawave-xray
/plugin install remnawave-xray@case211
/reload-plugins
```

Or through the UI: `/plugin` → **Marketplaces** tab → add `Case211/skill-remnawave-xray`, then install `remnawave-xray` from **Discover**.

**Manually** (without the marketplace): copy the `skills/remnawave-xray/` folder into your skills directory —
`~/.claude/skills/` (Windows: `%USERPROFILE%\.claude\skills\`) or `<project>/.claude/skills/`.

## Usage

Once installed, the skill loads **automatically** on relevant questions (Remnawave, selfsteal, Reality handshake, xray config, Caddyfile, mihomo, "node won't connect"), or you can invoke it explicitly: `/remnawave-xray`.

### Validating a config

```
python skills/remnawave-xray/validate.py <config.json> [Caddyfile]
```

A dependency-free (stdlib) validator that runs the consistency checklist as code: port 443, the `security × network` matrix, `flow` only on `raw`, 32-byte keys, shortIds (hex / even length / ≤16), `apple`/`icloud` in serverNames, `allowInsecure`, and — with a Caddyfile — `target` ↔ `https_port` and `xver` ↔ `proxy_protocol`. Placeholders like `<REALITY_PRIVATE_KEY>` are not treated as errors. Exit code 1 on errors.

## Other AI tools

The repository is **multi-agent** — entry points for popular tools (thin routers over the shared `skills/remnawave-xray/` content, no duplication):

| Tool | File |
|---|---|
| Claude Code | `skills/remnawave-xray/SKILL.md` (+ marketplace above) |
| OpenAI Codex / cross-standard AGENTS.md | `AGENTS.md` |
| Cursor | `.cursor/rules/remnawave-xray.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| Gemini CLI | `GEMINI.md` |
| Windsurf / Devin Desktop | `.windsurf/rules/` + `.devin/rules/remnawave-xray.md` |
| Codex / Gemini CLI / Copilot / Zed — lazy skill | `.agents/skills/remnawave-xray/SKILL.md` |

Usage: drop the repository (or just the files you need) into your project — each tool picks up its own entry point.

How it works: `AGENTS.md` is the cross-standard file (read by Codex, Cursor, Windsurf/Devin, Cline, Roo, Zed, Amp, Continue, and others), always-on and static. A **full skill** with progressive disclosure by description is the second standard ([agentskills.io](https://agentskills.io)), supported by Claude Code, Codex, Gemini CLI, GitHub Copilot, and Zed (via `.agents/skills/`/`.claude/skills/`). Here the skill lives in `skills/remnawave-xray/` (Claude Code plugin), while `.agents/skills/remnawave-xray/SKILL.md` provides **lazy loading by description** for Codex / Gemini CLI / Copilot / Zed (only `name` + `description` in context, the body loads on a relevant query). Tools without skill support (Cursor / Windsurf / Cline / …) get a router (`AGENTS.md`/`GEMINI.md`/rules). All of them point at the same reference (`reference/`, `generators`, `diagnostics`, `examples/`) — the content is never duplicated.

## Stack versions

Current as of the build date — verify before deploying:

| Component | Version |
|---|---|
| Remnawave panel/node | 2.8.0 |
| Xray-core | v26.6.27 (CalVer) |
| Caddy | 2.11.4 |
| mihomo (Clash.Meta) | 1.19.27 |

How to check what is current:

```
docker exec remnanode xray version
docker exec caddy-selfsteal caddy version
curl -s https://api.github.com/repos/XTLS/Xray-core/releases/latest | grep tag_name
curl -s https://api.github.com/repos/remnawave/panel/releases/latest | grep tag_name
curl -s https://api.github.com/repos/MetaCubeX/mihomo/releases/latest | grep tag_name
```

## Sources

Compiled from official documentation and source code, not blogs:

- Xray-core — [xtls.github.io](https://xtls.github.io/), [github.com/XTLS/Xray-core](https://github.com/XTLS/Xray-core) (including `infra/conf/*.go`), [llms-full.txt](https://xtls.github.io/llms-full.txt)
- Remnawave — [docs.rw](https://docs.rw/), `remnawave/{panel,node,backend}` sources
- Caddy — [caddyserver.com/docs](https://caddyserver.com/docs/)
- mihomo — [wiki.metacubex.one](https://wiki.metacubex.one/)
- selfsteal practice — community scripts (DigneZzZ and others)

## License

[AGPL-3.0](./LICENSE).

## Contributing

PRs/issues are welcome — especially clarifications on new Xray features (Hysteria 2, VLESS Encryption) and stack versions.

Before opening a PR: run `python tools/sync-check.py` — it verifies that the thin entry points (`AGENTS.md`, `GEMINI.md`, `.cursor`/`.windsurf`/`.devin`/`.github`, `.agents/`) reference the canonical skill and repeat the current versions from `skills/remnawave-xray/SKILL.md`. Run configs through `python skills/remnawave-xray/validate.py <config.json> [Caddyfile]`.