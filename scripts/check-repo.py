#!/usr/bin/env python3
"""Check the repo against the rules in AGENTS.md.

    python3 scripts/check-repo.py                     # rules for the current files
    python3 scripts/check-repo.py --base origin/main  # also require a version bump (CI)

Checks:
  - every skills/<name>/SKILL.md has frontmatter with name and description
  - name matches the folder and uses lowercase letters, digits, and hyphens (1 to 64)
  - description is 1 to 1024 characters and says when to use the skill ("Use when")
  - SKILL.md body is under 500 lines
  - every file in references/ is linked from SKILL.md or another reference file
  - README skills table: one row per skill, links work, rows in alphabetical order
  - EXAMPLES.md: one section per skill, in alphabetical order
  - README install commands use donnfelker/builder-skills and `--skill` names a real skill
  - plugin.json and marketplace.json are valid JSON; the version lives only in plugin.json
  - the Codex manifests are valid, and .codex-plugin/plugin.json's version matches
  - CHANGELOG.md has a heading for the current version
  - no em dashes, en dashes, or hype words in Markdown; no personal paths anywhere in skills/
With --base:
  - if skills/ or .claude-plugin/ changed, plugin.json's version must be higher than the base's
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO = "donnfelker/builder-skills"
HYPE = ["seamless", "robust", "powerful", "cutting-edge", "innovative"]
DASHES = re.compile("[–—]")
PERSONAL = re.compile(r"/Users/[A-Za-z]|/home/[a-z][a-z0-9_-]*/")
NAME = re.compile(r"^[a-z0-9-]{1,64}$")
VERSION = re.compile(r"^\d+\.\d+\.\d+$")

errors = []


def err(where, msg):
    errors.append("%s: %s" % (where, msg))


def rel(p):
    return str(p.relative_to(ROOT))


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text.replace("\r\n", "\n"), re.S)
    if not m:
        return None, text
    fields = {}
    for line in m.group(1).split("\n"):
        fm = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if fm:
            value = fm.group(2).strip()
            if value[:1] == '"':
                try:
                    value = json.loads(value)
                except ValueError:
                    value = value.strip('"')
            elif value[:1] == "'":
                value = value.strip("'").replace("''", "'")
            fields[fm.group(1)] = value
    return fields, text[m.end():]


def check_skill(folder):
    skill_md = folder / "SKILL.md"
    where = rel(skill_md)
    if not skill_md.is_file():
        err(rel(folder), "missing SKILL.md")
        return
    text = skill_md.read_text(encoding="utf-8")
    fields, body = frontmatter(text)
    if fields is None:
        err(where, "missing YAML frontmatter")
        return
    name, desc = fields.get("name"), fields.get("description")
    if not name:
        err(where, "frontmatter has no name")
    elif name != folder.name:
        err(where, "name %r does not match folder %r" % (name, folder.name))
    if not NAME.match(folder.name):
        err(where, "folder name must be 1 to 64 lowercase letters, digits, or hyphens")
    if not desc:
        err(where, "frontmatter has no description")
    else:
        if len(desc) > 1024:
            err(where, "description is %d characters (limit 1024)" % len(desc))
        if "Use when" not in desc:
            err(where, "description does not say when to use the skill (\"Use when ...\")")
    lines = body.count("\n") + 1
    if lines >= 500:
        err(where, "body is %d lines; move reference material to references/ (limit 500)" % lines)

    refs = folder / "references"
    if refs.is_dir():
        linked_text = text + "".join(p.read_text(encoding="utf-8", errors="replace")
                                     for p in refs.rglob("*") if p.is_file() and p.suffix == ".md")
        for p in sorted(refs.rglob("*")):
            if p.is_file() and p.relative_to(folder).as_posix() not in linked_text and p.name not in linked_text:
                err(rel(p), "not linked from SKILL.md or another reference file")


def check_text_rules():
    files = [ROOT / "README.md", ROOT / "CHANGELOG.md", ROOT / "AGENTS.md", ROOT / "EXAMPLES.md"] + sorted((ROOT / "skills").rglob("*.md"))
    for p in files:
        if not p.is_file():
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8").split("\n"), 1):
            if DASHES.search(line):
                err("%s:%d" % (rel(p), n), "em or en dash")
            if p.parent != ROOT or p.name == "README.md":
                for word in HYPE:
                    if re.search(r"\b%s\b" % re.escape(word), line, re.I):
                        err("%s:%d" % (rel(p), n), "hype word %r" % word)
    for p in sorted((ROOT / "skills").rglob("*")):
        if p.is_file() and p.suffix in (".md", ".py", ".json", ".sh", ".js", ".txt"):
            for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
                if PERSONAL.search(line):
                    err("%s:%d" % (rel(p), n), "personal path")


def check_examples(skill_names):
    path = ROOT / "EXAMPLES.md"
    if not path.is_file():
        err("EXAMPLES.md", "missing")
        return
    listed = re.findall(r"^## `([^`]+)`", path.read_text(encoding="utf-8"), re.M)
    for name in listed:
        if name not in skill_names:
            err("EXAMPLES.md", "section %r names a skill that does not exist" % name)
    for name in skill_names:
        if name not in listed:
            err("EXAMPLES.md", "skill %r has no example" % name)
    if listed != sorted(listed):
        err("EXAMPLES.md", "sections are not in alphabetical order")


def check_readme(skill_names):
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    rows = re.findall(r"^\|\s*\[([^\]]+)\]\(skills/([^)/]+)/?\)", readme, re.M)
    listed = [name for name, _ in rows]
    for name, target in rows:
        if name != target:
            err("README.md", "row %r links to skills/%s/" % (name, target))
        if not (ROOT / "skills" / target / "SKILL.md").is_file():
            err("README.md", "row %r links to a folder with no SKILL.md" % name)
    for name in skill_names:
        if name not in listed:
            err("README.md", "skill %r is missing from the skills table" % name)
    if listed != sorted(listed):
        err("README.md", "skills table rows are not in alphabetical order")
    for m in re.finditer(r"--skill\s+([a-z0-9-]+)", readme):
        if m.group(1) not in skill_names:
            err("README.md", "--skill %s names a skill that does not exist" % m.group(1))
    in_code = False
    for line in readme.split("\n"):
        if line.lstrip("> ").startswith("```"):
            in_code = not in_code
            continue
        if in_code and re.search(r"(npx skills add|marketplace add|git clone)", line) and REPO not in line:
            err("README.md", "install command does not use %s: %s" % (REPO, line.strip()))


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        err(rel(path), "not valid JSON: %s" % e)
        return None


def check_manifests():
    plugin = load_json(ROOT / ".claude-plugin" / "plugin.json")
    market = load_json(ROOT / ".claude-plugin" / "marketplace.json")
    version = None
    if plugin:
        version = plugin.get("version")
        if not version or not VERSION.match(str(version)):
            err(".claude-plugin/plugin.json", "version must be x.y.z")
        if plugin.get("name") != "builder-skills":
            err(".claude-plugin/plugin.json", "plugin name must stay builder-skills")
        if plugin.get("skills") != "./skills":
            err(".claude-plugin/plugin.json", "skills path must be ./skills")
    if market:
        if market.get("name") != "builder-skills":
            err(".claude-plugin/marketplace.json", "marketplace name must stay builder-skills")
        if "version" in json.dumps(market):
            err(".claude-plugin/marketplace.json", "no version here; plugin.json is the single place for it")
    codex = load_json(ROOT / ".codex-plugin" / "plugin.json")
    codex_market = load_json(ROOT / ".agents" / "plugins" / "marketplace.json")
    if codex:
        if codex.get("name") != "builder-skills":
            err(".codex-plugin/plugin.json", "plugin name must stay builder-skills")
        if codex.get("skills") not in ("./skills", "./skills/"):
            err(".codex-plugin/plugin.json", "skills path must be ./skills/")
        if version and codex.get("version") != version:
            err(".codex-plugin/plugin.json", "version %s must match .claude-plugin/plugin.json (%s)"
                % (codex.get("version"), version))
    if codex_market:
        names = [pl.get("name") for pl in codex_market.get("plugins", [])]
        if codex_market.get("name") != "builder-skills" or names != ["builder-skills"]:
            err(".agents/plugins/marketplace.json", "marketplace and plugin name must be builder-skills")
    if version:
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        if not re.search(r"^## %s\s*$" % re.escape(version), changelog, re.M):
            err("CHANGELOG.md", "no '## %s' heading for the current version" % version)
    return version


def newer(a, b):
    return tuple(map(int, a.split("."))) > tuple(map(int, b.split(".")))


def check_bump(base, version):
    try:
        changed = subprocess.run(["git", "diff", "--name-only", base + "...HEAD"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.split()
        old = json.loads(subprocess.run(["git", "show", base + ":.claude-plugin/plugin.json"], cwd=ROOT,
                                        capture_output=True, text=True, check=True).stdout).get("version")
    except (subprocess.CalledProcessError, ValueError) as e:
        err("git", "could not compare with %s: %s" % (base, e))
        return
    shipped = [f for f in changed if f.startswith(("skills/", ".claude-plugin/"))]
    if shipped and version and old and not newer(version, old):
        err(".claude-plugin/plugin.json",
            "skills changed (%s) but the version is still %s; bump it per AGENTS.md" % (", ".join(shipped[:3]), old))


def main():
    base = None
    if "--base" in sys.argv:
        base = sys.argv[sys.argv.index("--base") + 1]
    folders = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    for folder in folders:
        check_skill(folder)
    names = [f.name for f in folders]
    check_readme(names)
    check_examples(names)
    version = check_manifests()
    check_text_rules()
    if base:
        check_bump(base, version)
    if errors:
        print("%d problem(s):" % len(errors))
        for e in errors:
            print("  - " + e)
        sys.exit(1)
    print("OK: %d skills, version %s" % (len(names), version))


if __name__ == "__main__":
    main()
