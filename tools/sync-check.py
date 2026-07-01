#!/usr/bin/env python3
"""
sync-check.py — проверка, что кросс-tool точки входа не разъехались с каноном.

Канон — `skills/remnawave-xray/` (сам скилл). Тонкие роутеры (AGENTS.md, GEMINI.md,
.cursor/.windsurf/.devin/.github, .agents/) должны: существовать, ссылаться на канон,
не указывать на несуществующие файлы и повторять актуальные версии стека из SKILL.md.

Запуск из корня репозитория:  python tools/sync-check.py
Код выхода: 0 — синхронно; 1 — есть расхождения. Только stdlib.
"""
import sys
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CANON_DIR = "skills/remnawave-xray"
CANON_SKILL = os.path.join(CANON_DIR, "SKILL.md")

ENTRY_POINTS = [
    "AGENTS.md",
    "GEMINI.md",
    ".cursor/rules/remnawave-xray.mdc",
    ".devin/rules/remnawave-xray.md",
    ".github/copilot-instructions.md",
    ".windsurf/rules/remnawave-xray.md",
    ".agents/skills/remnawave-xray/SKILL.md",
]

PATH_RE = re.compile(r"skills/remnawave-xray/[^\s`)\]|]+")
problems = 0


def rel(p):
    return os.path.join(ROOT, *p.split("/"))


def read(p):
    with open(rel(p), "r", encoding="utf-8") as f:
        return f.read()


def canon_versions(txt):
    """Достаём эталонные версии из таблицы SKILL.md."""
    def grab(pat):
        m = re.search(pat, txt)
        return m.group(1) if m else None
    return {
        "Remnawave": grab(r"Remnawave panel/node\s*\|\s*([0-9][0-9.]*)"),
        "Xray-core": grab(r"Xray-core\s*\|\s*(v[0-9][0-9.]*)"),
        "Caddy":     grab(r"\|\s*Caddy\s*\|\s*([0-9][0-9.]*)"),
        "mihomo":    grab(r"mihomo \(Clash\.Meta\)\s*\|\s*([0-9][0-9.]*)"),
    }


def main():
    global problems

    if not os.path.isfile(rel(CANON_SKILL)):
        print(f"x канон не найден: {CANON_SKILL}")
        return 1
    versions = canon_versions(read(CANON_SKILL))
    missing_ver = [k for k, v in versions.items() if not v]
    if missing_ver:
        print(f"x не распарсил версии из {CANON_SKILL}: {', '.join(missing_ver)}")
        problems += 1
    print("Канон версий:", ", ".join(f"{k} {v}" for k, v in versions.items() if v))
    print()

    for ep in ENTRY_POINTS:
        if not os.path.isfile(rel(ep)):
            print(f"x {ep}: файл отсутствует")
            problems += 1
            continue
        txt = read(ep)
        issues = []

        # 1. ссылается на канон
        if CANON_DIR not in txt:
            issues.append(f"нет ссылки на {CANON_DIR}/")

        # 2. пути внутри канона не битые
        for m in sorted(set(PATH_RE.findall(txt))):
            target = rel(m)
            if not (os.path.isfile(target) or os.path.isdir(target)):
                issues.append(f"битый путь: {m}")

        # 3. версии совпадают — только если есть строка-декларация версий
        #    (слово «версии» И номер версии на той же строке; ссылка на SKILL.md не в счёт)
        if re.search(r"[Вв]ерси[а-я]*[^\n]*\d+\.\d+", txt):
            for comp, ver in versions.items():
                if ver and ver not in txt:
                    issues.append(f"версия {comp} {ver} не упомянута/устарела")

        if issues:
            problems += len(issues)
            print(f"x {ep}")
            for i in issues:
                print(f"    - {i}")
        else:
            print(f"OK {ep}")

    print()
    if problems:
        print(f"РАСХОЖДЕНИЯ: {problems}")
        return 1
    print("Всё синхронно с каноном.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
