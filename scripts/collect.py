#!/usr/bin/env python3
"""Collect RSS/Atom into a dated Markdown reading list. Python 3.10+."""
import argparse
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import html
import json
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode, urljoin
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

MAX_BYTES = 2_000_000

def date(value):
    try:
        result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        try: result = parsedate_to_datetime(value)
        except (ValueError, TypeError, AttributeError): return None
    if result is None or result.tzinfo is None: return None
    return result.astimezone(timezone.utc)

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]*>", "", value or ""))).strip()

def md(value):
    return re.sub(r"([\\`*_[\]<>])", r"\\\1", clean(value))

def canonical(value):
    parsed = urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Expected a public HTTPS article URL")
    query = [(k, v) for k, v in parse_qsl(parsed.query, keep_blank_values=True)
             if not k.lower().startswith("utm_") and k.lower() not in {"fbclid", "gclid"}]
    return urlunsplit((parsed.scheme, parsed.netloc.lower(), parsed.path or "/", urlencode(query), ""))

def parse(data, base):
    if len(data) > MAX_BYTES or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Feed too large or unsupported XML declarations")
    root = ET.fromstring(data)
    tag = lambda e: e.tag.rsplit("}", 1)[-1]
    if tag(root) not in {"rss", "feed", "RDF"}: raise ValueError("Not RSS/Atom")
    result, skipped = [], 0
    for entry in root.iter():
        if tag(entry) not in {"item", "entry"}: continue
        fields = {}
        links = []
        for child in entry:
            key = tag(child)
            fields.setdefault(key, "".join(child.itertext()))
            if key == "link":
                if child.attrib.get("rel", "alternate") == "alternate":
                    links.append(child.attrib.get("href") or child.text or "")
        timestamp = date(fields.get("pubDate") or fields.get("published") or fields.get("date") or fields.get("updated"))
        try: link = canonical(urljoin(base, links[0].strip())) if links else None
        except ValueError: link = None
        title = clean(fields.get("title"))
        if not timestamp or not link or not title:
            skipped += 1
            continue
        result.append({"title": title, "url": link, "published": timestamp.isoformat(),
                       "summary": clean(fields.get("description") or fields.get("summary"))[:1200]})
    return result, skipped

def fetch(url):
    canonical(url)
    with urlopen(Request(url, headers={"User-Agent": "OborovyRadar/1.0"}), timeout=20) as response:
        canonical(response.url)
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES: raise ValueError("Feed too large")
    return data

def collect(config, start, end, fixture_dir=None):
    items, problems, successful = {}, [], 0
    feeds = config.get("feeds")
    if not isinstance(feeds, list) or not feeds: raise ValueError("Missing feeds")
    if len(feeds) > 30: raise ValueError("Use at most 30 feeds")
    for i, source in enumerate(feeds, 1):
        try:
            name = clean(source["name"])
            url = canonical(source["url"])
            if fixture_dir is not None:
                filename = source.get("fixture", "")
                if not filename or Path(filename).name != filename: raise ValueError("Invalid fixture name")
                raw = (fixture_dir / filename).read_bytes()
            else:
                raw = fetch(url)
            entries, skipped = parse(raw, url)
            successful += 1
            if skipped: problems.append(f"Zdroj {i}: přeskočeno {skipped} položek bez použitelného data, titulku nebo HTTPS odkazu.")
            for entry in entries:
                if start <= date(entry["published"]) < end:
                    if entry["url"] in items:
                        if name not in items[entry["url"]]["sources"]: items[entry["url"]]["sources"].append(name)
                    else:
                        items[entry["url"]] = dict(entry, sources=[name])
        except Exception:
            # Do not echo a URL that might contain a private feed token.
            problems.append(f"Zdroj {i}: nepodařilo se načíst nebo zpracovat; ověřte konfiguraci a dostupnost.")
    return {"start":start.isoformat(), "end_exclusive":end.isoformat(), "sources_total":len(feeds),
        "sources_ok":successful, "problems":problems,
        "items":sorted(items.values(), key=lambda e:e["published"], reverse=True)}

def render(report):
    lines = ["# Podklady pro oborový radar", "", f"Od {report['start']} do {report['end_exclusive']} (konec se nezahrnuje).",
        f"Načtené zdroje: {report['sources_ok']}/{report['sources_total']}.", "",
        "Toto je seznam z feedů, nikoli ověřené shrnutí celých článků.", ""]
    for item in report["items"]:
        safe_url = item["url"].replace("(", "%28").replace(")", "%29").replace("<", "%3C").replace(">", "%3E")
        lines += [f"## {md(item['title'])}", "", f"{item['published']} · {md(', '.join(item['sources']))}",
                  "", f"[Původní článek](<{safe_url}>)", "", md(item["summary"]), ""]
    if not report["items"]: lines += ["V tomto období nebyly nalezeny použitelné položky.", ""]
    if report["problems"]: lines += ["## Omezení", ""] + ["- " + p for p in report["problems"]]
    return "\n".join(lines) + "\n"

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("config", type=Path)
    p.add_argument("--from", dest="start", required=True, help="ISO timestamp with timezone, inclusive")
    p.add_argument("--until", required=True, help="ISO timestamp with timezone, exclusive")
    p.add_argument("--fixture-dir", type=Path, help="Offline only: read fixtures instead of the network")
    p.add_argument("--output", required=True, type=Path)
    args = p.parse_args()
    try:
        start, end = date(args.start), date(args.until)
        if not start or not end or end <= start: raise ValueError("Invalid time range")
        if args.output.exists(): raise ValueError("Output exists")
        report = collect(json.loads(args.config.read_text(encoding="utf-8")), start, end, args.fixture_dir)
        with args.output.open("x", encoding="utf-8") as stream: stream.write(render(report))
        print(f"Zpracováno: {len(report['items'])} položek, {report['sources_ok']}/{report['sources_total']} zdrojů.")
        return 0 if not report["problems"] else 2
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        print("Sběr se nedokončil. Ověřte konfiguraci, časové okno a nový výstupní soubor.", file=sys.stderr)
        return 1

if __name__ == "__main__": sys.exit(main())
