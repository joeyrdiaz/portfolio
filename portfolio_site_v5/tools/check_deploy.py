"""Check the static site before Joey publishes it.

Run from anywhere:

    python3 tools/check_deploy.py

No installs. Exits 0 when every check passes.
"""
import json
import pathlib
import re
import struct
import subprocess
import sys
from html.parser import HTMLParser

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import render  # noqa: E402

KNOWN_TODOS = [
    "TODO: canonical URL",
]
LABEL = "Demo on synthetic data. Not a client result."
DASHES = ("\u2014", "\u2013", "\u2012", "\u2015")
SKIP_DIRS = {".git", "uploads", "__pycache__", "node_modules"}


class Collector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.skip = 0
        self.text = []
        self.attrs = []
        self.ids = set()
        self.links = []
        self.metas = []

    def handle_starttag(self, tag, attrs):
        data = dict(attrs)
        if tag in ("script", "style"):
            self.skip += 1
        if "id" in data:
            self.ids.add(data["id"])
        for key in ("href", "src"):
            if key in data:
                self.links.append((tag, key, data[key], data.get("rel", "")))
        if tag == "meta":
            self.metas.append(data)
        if self.skip:
            return
        for key in ("alt", "aria-label", "placeholder", "title"):
            if data.get(key):
                self.attrs.append((f"{tag}[{key}]", data[key]))

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip and data.strip():
            self.text.append(data)


def png_size(path):
    with open(path, "rb") as handle:
        sig = handle.read(8)
        if sig != b"\x89PNG\r\n\x1a\n":
            raise ValueError("not a png")
        handle.read(4)
        handle.read(4)
        width, height = struct.unpack(">II", handle.read(8))
        return width, height


def visible_bits(path):
    parser = Collector()
    parser.feed(path.read_text(encoding="utf-8"))
    bits = [("text", "\n".join(parser.text))]
    bits.extend(parser.attrs)
    for meta in parser.metas:
        name = (meta.get("name") or meta.get("property") or "").lower()
        if name == "viewport":
            continue
        if meta.get("content") and (
            name in {"description", "twitter:title", "twitter:description", "twitter:image:alt"}
            or name.startswith("og:")
        ):
            bits.append((f"meta:{name}", meta["content"]))
    title = re.search(r"<title>(.*?)</title>", path.read_text(encoding="utf-8"), re.I | re.S)
    if title:
        bits.append(("title", title.group(1).strip()))
    return parser, bits


def fail(errors, message):
    errors.append(message)


BANNED_NAMES = ("kai" + "ros", "meridian" + "link", "lone " + "star")


def mentions_banned(text):
    return any(re.search(name, text, re.I) for name in BANNED_NAMES)


def check_dashes(errors, label, text):
    for dash in DASHES:
        if dash in text:
            fail(errors, f"{label} contains a dash punctuation character")
    if " - " in text:
        fail(errors, f"{label} contains a spaced hyphen")
    for match in re.finditer(r"[A-Za-z0-9]-[A-Za-z0-9]", text):
        start = max(0, match.start() - 24)
        fail(errors, f"{label} contains a hyphenated word near: {text[start:match.end() + 24]!r}")


def check_html(errors, path):
    parser, bits = visible_bits(path)
    raw = path.read_text(encoding="utf-8")
    for kind, text in bits:
        if mentions_banned(text):
            fail(errors, f"{path.name} {kind} mentions a forbidden name")
        check_dashes(errors, f"{path.name} {kind}", text)
    for tag, key, value, rel in parser.links:
        if value.startswith(("mailto:", "data:", "#")):
            continue
        if "TODO" in value:
            continue
        if value.startswith(("http://", "https://", "//")):
            fail(errors, f"{path.name} external resource {key}={value}")
            continue
        if value.startswith("/"):
            fail(errors, f"{path.name} root relative link breaks project sites: {value}")
            continue
        clean = value.split("#", 1)[0].split("?", 1)[0]
        if clean and not (path.parent / clean).exists():
            fail(errors, f"{path.name} missing file for {value}")
        if tag == "a" and value.startswith("#"):
            pass
    for tag, key, value, rel in parser.links:
        if tag == "a" and value.startswith("#") and value != "#":
            anchor = value[1:]
            if anchor not in parser.ids:
                fail(errors, f"{path.name} anchor #{anchor} has no matching id")
    if re.search(r"url\(\s*['\"]?https?:", raw, re.I):
        fail(errors, f"{path.name} CSS points at an external URL")
    return parser


def check_todos(errors, html, readme):
    for phrase in KNOWN_TODOS:
        if phrase not in html:
            fail(errors, f"index.html is missing {phrase}")
        if phrase not in readme:
            fail(errors, f"README checklist is missing {phrase}")
    index = 0
    while True:
        found = html.find("TODO", index)
        if found < 0:
            break
        if not any(html.startswith(phrase, found) for phrase in KNOWN_TODOS):
            fail(errors, "unexpected TODO in index.html: " + html[found:found + 48].replace("\n", " "))
        index = found + 4


def check_numbers(errors, html):
    data = json.loads((ROOT / "demo_numbers.json").read_text(encoding="utf-8"))
    start_bits = data["period_start"]
    expect = [
        render.pct(data["close_rate_under_15m"]),
        render.pct(data["close_rate_over_24h"]),
        render.pct(data["close_rate"]),
        render.k_money(data["unconverted_quote_value_over_14_days"]),
        f'{data["unconverted_quotes_over_14_days"]:,}',
        f'{data["total_leads"]:,}',
        data["company"],
        f'value="{round(data["total_leads"] / (((int(start_bits[0:4]) * 12 + int(start_bits[5:7])) and 1) or 1))}"',
    ]
    # Recompute defaults the same way the renderer does.
    from datetime import date
    start = date.fromisoformat(data["period_start"])
    end = date.fromisoformat(data["as_of"])
    months = (end.year - start.year) * 12 + end.month - start.month + 1
    jobs = data["jobs_by_job_type"]
    tickets = data["avg_ticket_by_job_type"]
    avg_ticket = round(sum(tickets[name] * jobs[name] for name in jobs) / sum(jobs.values()))
    leads = round(data["total_leads"] / months)
    close = f'{data["close_rate"] * 100:.1f}'
    hours = f'{data["median_response_minutes"] / 60:.1f}'
    for snippet in (
        f'value="{leads}"',
        f'value="{avg_ticket}"',
        f'value="{close}"',
        f'value="{hours}"',
        render.pct(data["close_rate_under_15m"]),
        render.pct(data["close_rate_over_24h"]),
        render.pct(data["close_rate"]),
        render.k_money(data["unconverted_quote_value_over_14_days"]),
        f'{data["unconverted_quotes_over_14_days"]:,} quotes',
        f'{data["total_leads"]:,}',
        data["company"],
        render.money(tickets["Replacement"]),
        json.dumps({name: row["close_rate"] for name, row in data["close_rate_by_response_bucket"].items()}),
        *[f'{count:,}' for count in data["leads_by_source"].values()],
        *[render.k_money(row["value"]) for row in data["awaiting_quote_value_by_age"]],
    ):
        if snippet not in html:
            fail(errors, f"rendered page is missing demo figure {snippet}")
    if "<img" in html:
        fail(errors, "index.html still uses chart images; charts should be drawn in the page")
    if html.count(LABEL) < 10:
        fail(errors, f"demo label appears {html.count(LABEL)} times, expected at least 10")
    lowered = html.lower()
    for banned in ("looker", "built in power bi", "built with power bi", "in power bi", "power bi dashboard"):
        if banned in lowered:
            fail(errors, f"index.html claims a dashboard built in a BI tool: {banned}")


def check_readme(errors, text):
    if mentions_banned(text):
        fail(errors, "README mentions a forbidden name")
    prose = re.sub(r"```.*?```", "", text, flags=re.S)
    prose = re.sub(r"`[^`]+`", "", prose)
    prose = re.sub(r"https?://\S+", "", prose)
    for dash in DASHES:
        if dash in prose:
            fail(errors, "README prose contains dash punctuation")
    if " - " in prose:
        fail(errors, "README prose contains a spaced hyphen")
    for match in re.finditer(r"[A-Za-z0-9]-[A-Za-z0-9]", prose):
        start = max(0, match.start() - 30)
        fail(errors, "README prose contains a hyphenated word near: " + prose[start:match.end() + 30].replace("\n", " "))


def check_tree_for_banned_name(errors):
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if mentions_banned(text):
            fail(errors, f"{path.relative_to(ROOT)} contains a forbidden name")


def main():
    errors = []
    required = [
        "index.html",
        "404.html",
        "favicon.svg",
        "robots.txt",
        ".nojekyll",
        "demo_numbers.json",
        "README.md",
        ".github/workflows/pages.yml",
        "assets/og.png",
        "tools/template.html",
        "tools/render.py",
        "tests/calc.test.js",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            fail(errors, f"missing {rel}")
    html_path = ROOT / "index.html"
    readme = (ROOT / "README.md").read_text(encoding="utf-8") if (ROOT / "README.md").exists() else ""
    if html_path.exists():
        html = html_path.read_text(encoding="utf-8")
        check_html(errors, html_path)
        check_todos(errors, html, readme)
        check_numbers(errors, html)
    if (ROOT / "404.html").exists():
        check_html(errors, ROOT / "404.html")
    if readme:
        check_readme(errors, readme)
    check_tree_for_banned_name(errors)
    og = ROOT / "assets" / "og.png"
    if og.exists():
        try:
            size = png_size(og)
        except ValueError as exc:
            fail(errors, f"og.png {exc}")
        else:
            if size != (1200, 630):
                fail(errors, f"og.png is {size[0]}x{size[1]}, expected 1200x630")
    workflow = ROOT / ".github" / "workflows" / "pages.yml"
    if workflow.exists():
        text = workflow.read_text(encoding="utf-8")
        for needle in (
            "actions/checkout@",
            "actions/configure-pages@",
            "actions/upload-pages-artifact@",
            "actions/deploy-pages@",
            "pages: write",
            "id-token: write",
            "cancel-in-progress:",
        ):
            if needle not in text:
                fail(errors, f"pages workflow is missing {needle}")
        if "branches:" not in text or "main" not in text:
            fail(errors, "pages workflow does not run on main")
    proc = subprocess.run(
        ["node", "tests/calc.test.js"],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        fail(errors, "calculator tests failed:\n" + proc.stdout + proc.stderr)
    else:
        print(proc.stdout.strip())
    if errors:
        print(f"\n{len(errors)} check(s) failed:")
        for item in errors:
            print(" - " + item)
        return 1
    print("\nAll deployment checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
