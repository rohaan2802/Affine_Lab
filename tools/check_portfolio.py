"""Verify local links, exact figure parity, PNG dimensions and saved hashes."""

import hashlib
from html.parser import HTMLParser
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
from PIL import Image
import project_reference

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.ids = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            self.ids.append(attrs["id"])
        for name in ("href", "src"):
            if attrs.get(name):
                self.links.append(attrs[name])


def main():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    md = (ROOT / "README.md").read_text(encoding="utf-8")
    parser = Links()
    parser.feed(html)
    assert len(parser.ids) == len(set(parser.ids)), "Duplicate HTML ids"
    local = 0
    for url in parser.links:
        parts = urlsplit(url)
        if parts.scheme or parts.netloc:
            continue
        path = ROOT / unquote(parts.path)
        assert path.exists(), f"Missing site target {url}"
        if not parts.path and parts.fragment:
            assert parts.fragment in parser.ids, url
        local += 1
    figures = json.loads(
        (ROOT / "assets/figures/manifest.json").read_text(encoding="utf-8")
    )
    assert len(figures) == 24
    for block in project_reference.sections():
        assert block["title"] in md, "Missing README reference section"
        assert f'id="reference-{block["id"]}"' in html, (
            "Missing webpage reference section"
        )
        for paragraph in block["paragraphs"]:
            assert paragraph in md, "Detailed reference content drifted from README"
            assert escape(paragraph) in html, (
                "Detailed reference content drifted from webpage"
            )
    for folder in ("full", "previews"):
        assert len(list((ROOT / "assets/figures" / folder).glob("*.png"))) == 24, (
            "Stale figure files remain"
        )
    assert "FAST-NUCES" in md, "Author affiliation changed unexpectedly"
    assert [f["id"] for f in figures] == list(range(1, 25))
    last = -1
    for f in figures:
        for kind, size in [("full", (1440, 900)), ("preview", (960, 600))]:
            with Image.open(ROOT / f[kind]) as image:
                assert image.size == size, f[kind]
        expected = f"[![{f['title']}]({f['preview']})]({f['full']})"
        position = md.index(expected)
        assert position > last
        last = position
        assert f["caption"] in md
        assert f"### Figure {f['id']:02} — {f['title']}" in md
    javascript = (ROOT / "assets/js/portfolio_data.js").read_text(encoding="utf-8")
    assert (
        json.loads(
            javascript.split("window.AFFINE_FIGURES=", 1)[1].split(
                ";\nwindow.AFFINE_SAMPLE=", 1
            )[0]
        )
        == figures
    )
    for match in re.finditer(r"\]\(([^)]+)\)", md):
        url = match.group(1)
        parts = urlsplit(url)
        if not parts.scheme and parts.path:
            assert (ROOT / unquote(parts.path)).exists(), f"Missing README target {url}"
    table = md.split("## Live Links", 1)[1].split("## Contents", 1)[0]
    documentation_links = 0
    for document in (ROOT / "docs").glob("*.md"):
        for match in re.finditer(
            r"\]\(([^)]+)\)", document.read_text(encoding="utf-8")
        ):
            parts = urlsplit(match.group(1))
            if not parts.scheme and parts.path:
                assert (document.parent / unquote(parts.path)).exists(), (
                    f"Missing documentation target in {document.name}: {parts.path}"
                )
                documentation_links += 1
    assert len(re.findall(r"\]\(https://", table)) == 3
    for file in ["assets/css/site.css", "assets/js/site.js"]:
        assert "fonts-placeholder" not in (ROOT / file).read_text(encoding="utf-8")
    manifest = json.loads(
        (ROOT / "reports/replay_demo/manifest.json").read_text(encoding="utf-8")
    )
    for item in manifest["files"]:
        raw = (ROOT / "reports/replay_demo" / item["path"]).read_bytes()
        assert (
            len(raw) == item["bytes"]
            and hashlib.sha256(raw).hexdigest() == item["sha256"]
        )
    print(
        f"PASS: {local} local site targets, {documentation_links} documentation links, shared reference parity, 24 figure/caption/order matches, 48 dimensions, 3 HTTPS table links, replay hashes"
    )


if __name__ == "__main__":
    main()
