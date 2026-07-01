#!/usr/bin/env python3
"""
Genera feed.xml (RSS 2.0) y sitemap.xml a partir de data/articles.json y el
"front matter" de cada artículo. Son archivos estáticos: basta con volver a
ejecutar este script tras publicar y confirmar los cambios en git.

Uso:
    python3 tools/build_feed.py

Configuración: data/site.json (dominio, título, descripción).
Sugerencia: ejecútelo después de tools/new_post.py, o añádalo como paso de
compilación en Cloudflare Pages (comando: python3 tools/build_feed.py).
"""
import json
import re
import sys
import email.utils
import datetime
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"


def parse_front_matter(text):
    meta = {}
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n?", text, re.S)
    if not m:
        return meta, text
    body = text[m.end():]
    key = None
    for line in m.group(1).splitlines():
        if not line.strip():
            continue
        li = re.match(r"^\s*-\s+(.*)$", line)
        if li and key:
            meta.setdefault(key, [])
            if not isinstance(meta[key], list):
                meta[key] = [meta[key]]
            meta[key].append(unquote(li.group(1)))
            continue
        kv = re.match(r"^([A-Za-z0-9_]+):\s*(.*)$", line)
        if kv:
            key = kv.group(1)
            meta[key] = [] if kv.group(2) == "" else unquote(kv.group(2))
    return meta, body


def unquote(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    return v


def excerpt(body):
    pre = body.split("<!-- more -->")[0]
    pre = re.sub(r"^#.*$", "", pre, flags=re.M)
    pre = re.sub(r"^\s*>\s?", "", pre, flags=re.M)
    pre = re.sub(r"[*_`>#]", "", pre)
    pre = re.sub(r"\s+", " ", pre).strip()
    if len(pre) > 240:
        pre = re.sub(r"\s+\S*$", "", pre[:240]) + "…"
    return pre


def rfc822(iso):
    y, m, d = (int(x) for x in str(iso).split("-")[:3])
    dt = datetime.datetime(y, m, d, 12, 0, 0, tzinfo=datetime.timezone.utc)
    return email.utils.format_datetime(dt)


def main():
    site = json.loads((ROOT / "data" / "site.json").read_text(encoding="utf-8"))
    order = json.loads((ROOT / "data" / "articles.json").read_text(encoding="utf-8"))["articles"]
    base = site["url"].rstrip("/")

    posts = []
    for slug in order:
        path = ARTICLES / f"{slug}.md"
        if not path.exists():
            print(f"aviso: falta articles/{slug}.md; se omite", file=sys.stderr)
            continue
        meta, body = parse_front_matter(path.read_text(encoding="utf-8"))
        posts.append({
            "slug": slug,
            "title": meta.get("title", slug),
            "date": str(meta.get("date", "")),
            "desc": excerpt(body),
            "url": f"{base}/#/articulo/{slug}",
        })
    posts.sort(key=lambda p: p["date"], reverse=True)

    # ---- RSS 2.0 ----------------------------------------------------------
    items = []
    for p in posts:
        items.append(
            "    <item>\n"
            f"      <title>{escape(p['title'])}</title>\n"
            f"      <link>{escape(p['url'])}</link>\n"
            f"      <guid isPermaLink=\"false\">pluma-y-tertulia:{escape(p['slug'])}</guid>\n"
            f"      <pubDate>{rfc822(p['date'])}</pubDate>\n"
            f"      <description>{escape(p['desc'])}</description>\n"
            "    </item>"
        )
    rss = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{escape(site['title'])}</title>\n"
        f"    <link>{escape(base + '/')}</link>\n"
        f"    <description>{escape(site['description'])}</description>\n"
        f"    <language>{escape(site.get('language', 'es'))}</language>\n"
        f"    <atom:link href=\"{escape(base + '/feed.xml')}\" rel=\"self\" type=\"application/rss+xml\"/>\n"
        + "\n".join(items) + "\n"
        "  </channel>\n"
        "</rss>\n"
    )
    (ROOT / "feed.xml").write_text(rss, encoding="utf-8")

    # ---- sitemap ----------------------------------------------------------
    # Con rutas de almohadilla (#) los rastreadores sólo ven la portada; el
    # sitemap declara al menos la raíz con la fecha del último texto.
    lastmod = posts[0]["date"] if posts else datetime.date.today().isoformat()
    sitemap = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{escape(base + '/')}</loc><lastmod>{lastmod}</lastmod></url>\n"
        "</urlset>\n"
    )
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    print(f"feed.xml     ({len(posts)} textos)")
    print("sitemap.xml")


if __name__ == "__main__":
    main()
