"""Validate essential SEO metadata in the generated Jekyll site."""
import json
import sys
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from pathlib import Path

root = Path(sys.argv[1])
base = "https://vwtyler.dev"
errors = []


class Metadata(HTMLParser):
    def __init__(self):
        super().__init__()
        self.meta = {}
        self.canonical = None
        self.structured = []
        self.in_json = False
        self.buffer = ""

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            for key in ("name", "property"):
                if a.get(key):
                    self.meta[a[key]] = a.get("content", "")
        if tag == "link" and a.get("rel") == "canonical":
            self.canonical = a.get("href")
        if tag == "script" and a.get("type") == "application/ld+json":
            self.in_json = True
            self.buffer = ""

    def handle_data(self, data):
        if self.in_json:
            self.buffer += data

    def handle_endtag(self, tag):
        if tag == "script" and self.in_json:
            self.structured.append(self.buffer)
            self.in_json = False


def require(condition, message):
    if not condition:
        errors.append(message)


sitemap = ET.parse(root / "sitemap.xml")
urls = {node.text for node in sitemap.iter("{*}loc")}
robots = (root / "robots.txt").read_text()
require(f"Sitemap: {base}/sitemap.xml" in robots, "robots.txt missing sitemap URL")
require(not any(line.strip().lower() == "disallow: /" for line in robots.splitlines()),
        "robots.txt contains a site-wide crawl block")
ET.parse(root / "feed.xml")
posts = sorted((root / "posts").glob("*/index.html"))
require(bool(posts), "No generated posts found")

for file in [root / "index.html", *posts]:
    route = "/" + file.parent.relative_to(root).as_posix().strip("./")
    if not route.endswith("/"):
        route += "/"
    expected = base + route
    m = Metadata()
    m.feed(file.read_text())
    require(m.canonical == expected, f"{file}: incorrect canonical URL")
    require(bool(m.meta.get("description")), f"{file}: missing description")
    require("noindex" not in m.meta.get("robots", "").lower(), f"{file}: noindex")
    for key in ("og:title", "og:description", "og:image", "og:url", "twitter:card"):
        require(bool(m.meta.get(key)), f"{file}: missing {key}")
    require(m.meta.get("og:url") == expected, f"{file}: incorrect og:url")
    require(bool(m.structured), f"{file}: missing JSON-LD")
    for block in m.structured:
        try:
            json.loads(block)
        except ValueError:
            errors.append(f"{file}: invalid JSON-LD")
    if file in posts:
        require(expected in urls, f"{file}: missing from sitemap")

if errors:
    sys.exit("\n".join(errors))
print(f"SEO checks passed for homepage and {len(posts)} posts.")
