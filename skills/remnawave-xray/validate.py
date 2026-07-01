#!/usr/bin/env python3
"""
validate.py — проверка согласованности конфигов selfsteal-ноды
(Remnawave Config Profile / Xray Reality + опционально Caddyfile).

Прогоняет чек-лист согласованности из generators.md автоматически: порт 443,
матрица security x network, flow только на raw, target <-> Caddy-порт, ключи,
serverNames/shortIds, xver <-> proxy_protocol, apple/icloud, allowInsecure.

Использование:
    python validate.py <xray-config.json> [Caddyfile]

Коды выхода: 0 — ошибок нет (warning допустимы); 1 — есть ошибки; 2 — не прочитал вход.
Плейсхолдеры вида <REALITY_PRIVATE_KEY> ошибкой не считаются — помечаются как «не подставлено».
Только stdlib, зависимостей нет.
"""
import sys
import json
import re
import base64

ERRORS, WARNINGS, NOTES = [], [], []
def err(m):  ERRORS.append(m)
def warn(m): WARNINGS.append(m)
def note(m): NOTES.append(m)

PLACEHOLDER = re.compile(r"^\s*<[^>]+>\s*$")
HEX = re.compile(r"^[0-9a-fA-F]*$")
LOCALHOST = {"127.0.0.1", "localhost", "::1", ""}


def is_placeholder(v):
    return isinstance(v, str) and bool(PLACEHOLDER.match(v))


def b64_bytes(s):
    """Длина в байтах для base64 (RawURL или std), либо None если не парсится."""
    s2 = s.strip().replace("-", "+").replace("_", "/")
    s2 += "=" * (-len(s2) % 4)
    try:
        return len(base64.b64decode(s2, validate=False))
    except Exception:
        return None


def parse_hostport(target):
    """'127.0.0.1:9443' | '9443' | '/path.sock' | '<PH>' -> (host, port|None, kind)."""
    if is_placeholder(target):
        return (None, None, "placeholder")
    t = str(target).strip()
    if t.startswith("/") or t.endswith(".sock"):
        return (t, None, "unix")
    if ":" in t:
        host, _, port = t.rpartition(":")
        return (host, port_int(port), "hostport")
    if t.isdigit():
        return ("127.0.0.1", int(t), "port")
    return (t, None, "host")


def port_int(tok):
    """Порт из '9443' или '{$SELF_STEAL_PORT:9443}' -> int|None (None если только плейсхолдер)."""
    tok = str(tok).strip()
    if tok.isdigit():
        return int(tok)
    m = re.search(r"\{\$[A-Z0-9_]+:(\d+)\}", tok)   # {$VAR:default}
    if m:
        return int(m.group(1))
    return None


def check_reality_inbound(ib):
    tag = ib.get("tag", "<no-tag>")
    ss = ib.get("streamSettings", {}) or {}
    rs = ss.get("realitySettings", {}) or {}
    listen = ib.get("listen", "0.0.0.0")
    port = ib.get("port")
    public = str(listen) in ("0.0.0.0", "", "::")

    # 1. Порт 443 (только для публично слушающих; localhost-инбаунд за реверс-прокси — норма)
    if port != 443:
        if public:
            err(f"[{tag}] публичный Reality-инбаунд на порту {port}, а не 443 "
                f"(ядро помечает не-443 warning'ом -> быстрый бан IP)")
        else:
            note(f"[{tag}] порт {port} на {listen} — ок для CDN-инбаунда за реверс-прокси")

    # 2. security x network
    network = ss.get("network")
    if network not in ("raw", "xhttp", "grpc"):
        err(f"[{tag}] security=reality несовместим с network={network!r} "
            f"(только raw/xhttp/grpc)")

    # 3. flow только xtls-rprx-vision и только на raw
    for cl in ib.get("settings", {}).get("clients", []) or []:
        flow = cl.get("flow", "")
        if flow == "xtls-rprx-vision" and network != "raw":
            err(f"[{tag}] flow=xtls-rprx-vision требует network=raw (сейчас {network!r})")
        elif flow and flow != "xtls-rprx-vision":
            warn(f"[{tag}] flow={flow!r} — legacy XTLS-flow мертвы, только xtls-rprx-vision")

    # 4. serverNames
    sns = rs.get("serverNames")
    domains = []
    if not sns:
        err(f"[{tag}] пустой serverNames (обязателен непустой список)")
    else:
        for sn in sns:
            if is_placeholder(sn):
                note(f"[{tag}] serverNames содержит плейсхолдер {sn!r}")
                continue
            domains.append(sn)
            if re.search(r"(apple|icloud)", sn, re.I):
                err(f"[{tag}] serverNames={sn!r} — apple/icloud палятся, ядро warning'ит + бан")

    # 5. privateKey
    pk = rs.get("privateKey")
    if pk is None:
        err(f"[{tag}] нет privateKey в realitySettings")
    elif is_placeholder(pk):
        note(f"[{tag}] privateKey не подставлен (плейсхолдер)")
    else:
        n = b64_bytes(pk)
        if n is None:
            err(f"[{tag}] privateKey не декодируется как base64 (нужен x25519, 32 байта)")
        elif n != 32:
            err(f"[{tag}] privateKey декодируется в {n} байт, нужно ровно 32 "
                f"(перегенерировать xray x25519)")

    # 6. shortIds
    sids = rs.get("shortIds")
    if sids is None:
        err(f"[{tag}] нет shortIds (допустимо [\"\"], но поле обязательно)")
    else:
        for sid in sids:
            if is_placeholder(sid):
                note(f"[{tag}] shortId-плейсхолдер {sid!r}")
                continue
            if sid == "":
                continue
            if not HEX.match(sid):
                err(f"[{tag}] shortId={sid!r} не hex")
            elif len(sid) % 2 != 0:
                err(f"[{tag}] shortId={sid!r} нечётной длины")
            elif len(sid) > 16:
                err(f"[{tag}] shortId={sid!r} длиннее 16 hex-символов")

    # 7. xver
    xver = rs.get("xver", 0)
    if xver not in (0, 1, 2):
        err(f"[{tag}] xver={xver} вне диапазона 0/1/2")

    # 8. show
    if rs.get("show") is True:
        warn(f"[{tag}] show=true — в проде должно быть false")

    # target
    target = rs.get("target", rs.get("dest"))
    if target is None:
        err(f"[{tag}] нет target/dest в realitySettings")
    thost, tport, tkind = parse_hostport(target)

    return {"tag": tag, "target_host": thost, "target_port": tport,
            "target_kind": tkind, "xver": xver, "domains": domains}


def parse_caddyfile(text):
    info = {"https_port": None, "site_port": None, "proxy_protocol": False,
            "domains": []}
    m = re.search(r"^\s*https_port\s+(\S+)", text, re.M)
    if m:
        info["https_port"] = port_int(m.group(1))
    info["proxy_protocol"] = bool(re.search(r"\bproxy_protocol\b", text))
    # site-заголовок вида DOMAIN:PORT { — берём первый с портом
    for m in re.finditer(r"^\s*([^\s{#][^{\n]*?):(\S+?)\s*\{", text, re.M):
        host, port = m.group(1).strip(), port_int(m.group(2))
        if port:
            info["site_port"] = info["site_port"] or port
        if host and not host.startswith(":") and "$" not in host:
            info["domains"].append(host)
    return info


def cross_check(reality, caddy):
    tag = reality["tag"]
    cport = caddy["https_port"] or caddy["site_port"]
    tport = reality["target_port"]

    if reality["target_kind"] == "placeholder":
        note(f"[{tag}] target — плейсхолдер, порт с Caddy не сверить")
    elif reality["target_host"] in LOCALHOST and tport and cport and tport != cport:
        err(f"[{tag}] target-порт {tport} != Caddy-порт {cport} "
            f"(должны совпадать: Xray target <-> Caddy https_port)")
    elif reality["target_host"] in LOCALHOST and tport and cport:
        note(f"[{tag}] target-порт {tport} совпал с Caddy {cport}")

    if reality["xver"] in (1, 2) and not caddy["proxy_protocol"]:
        err(f"[{tag}] xver={reality['xver']}, но в Caddyfile нет proxy_protocol "
            f"(Caddy увидит 127.0.0.1 вместо реального IP)")
    if reality["xver"] == 0 and caddy["proxy_protocol"]:
        err(f"[{tag}] xver=0, но в Caddyfile есть proxy_protocol "
            f"(Caddy будет ждать несуществующий PROXY-заголовок)")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    try:
        with open(sys.argv[1], "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception as e:
        print(f"[fatal] не прочитал {sys.argv[1]}: {e}")
        return 2

    raw = json.dumps(cfg)
    if '"allowInsecure"' in raw:
        err("allowInsecure присутствует в конфиге (выпилен из ядра v26.2.6 — убрать)")

    reality_inbounds = [
        ib for ib in cfg.get("inbounds", [])
        if ib.get("protocol") == "vless"
        and (ib.get("streamSettings", {}) or {}).get("security") == "reality"
    ]
    if not reality_inbounds:
        warn("не найден ни один VLESS+Reality inbound — проверять нечего")

    realities = [check_reality_inbound(ib) for ib in reality_inbounds]

    caddy = None
    if len(sys.argv) >= 3:
        try:
            with open(sys.argv[2], "r", encoding="utf-8") as f:
                caddy = parse_caddyfile(f.read())
        except Exception as e:
            print(f"[fatal] не прочитал Caddyfile {sys.argv[2]}: {e}")
            return 2
        for r in realities:
            cross_check(r, caddy)

    for m in NOTES:
        print(f"  · {m}")
    for m in WARNINGS:
        print(f"  ! {m}")
    for m in ERRORS:
        print(f"  x {m}")

    print()
    if ERRORS:
        print(f"ПРОВАЛ: {len(ERRORS)} ошибок, {len(WARNINGS)} предупреждений")
        return 1
    print(f"OK: ошибок нет, {len(WARNINGS)} предупреждений, {len(NOTES)} заметок")
    return 0


if __name__ == "__main__":
    sys.exit(main())
