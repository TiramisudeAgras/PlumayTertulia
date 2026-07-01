#!/usr/bin/env python3
"""
Andamiaje para publicar en Pluma y Tertulia.

Crea articles/<slug>.md a partir de una plantilla y lo registra al principio
de data/articles.json. Publicar sigue siendo predecible: un comando, dos efectos.

Uso:
    python3 tools/new_post.py "Título del texto" --format essay --author Chachalingo
    python3 tools/new_post.py "Vacío" -f poetry -a MoccaBM --date 2025-02-26 --lang es

Formatos: poetry | essay | story   (alias: poesia/poema, ensayo, cuento/relato)
"""
import argparse
import datetime
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLES = ROOT / "articles"
DATA = ROOT / "data" / "articles.json"
AUTHORS = ROOT / "data" / "authors.json"
TEMPLATES = ROOT / "templates"

FORMATS = {
    "poetry": ("poesia.md", "Poesía"),
    "poesia": ("poesia.md", "Poesía"),
    "poema": ("poesia.md", "Poesía"),
    "essay": ("ensayo.md", "Ensayos"),
    "ensayo": ("ensayo.md", "Ensayos"),
    "story": ("cuento.md", "Cuentos/Novelas"),
    "cuento": ("cuento.md", "Cuentos/Novelas"),
    "relato": ("cuento.md", "Cuentos/Novelas"),
}
CANON = {"poetry": "poetry", "poesia": "poetry", "poema": "poetry",
         "essay": "essay", "ensayo": "essay",
         "story": "story", "cuento": "story", "relato": "story"}


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def main() -> int:
    p = argparse.ArgumentParser(description="Crea y registra un nuevo artículo.")
    p.add_argument("title", help="Título del texto (entre comillas).")
    p.add_argument("-f", "--format", default="essay", help="poetry | essay | story")
    p.add_argument("-a", "--author", default="Chachalingo", help="handle de autor (ver data/authors.json)")
    p.add_argument("-d", "--date", default=datetime.date.today().isoformat(), help="AAAA-MM-DD")
    p.add_argument("-l", "--lang", default="es", help="es | en")
    p.add_argument("-s", "--slug", default=None, help="slug personalizado (por defecto se deriva del título)")
    args = p.parse_args()

    fmt_key = args.format.lower()
    if fmt_key not in FORMATS:
        print(f"Formato desconocido: {args.format}. Use poetry | essay | story.", file=sys.stderr)
        return 2
    tpl_name, genre = FORMATS[fmt_key]
    fmt = CANON[fmt_key]

    # validar autor (aviso, no bloqueo)
    if AUTHORS.exists():
        authors = json.loads(AUTHORS.read_text(encoding="utf-8"))
        if args.author not in authors:
            print(f"Aviso: el autor '{args.author}' no está en data/authors.json. "
                  f"Añádelo allí o el nombre se mostrará tal cual.", file=sys.stderr)

    slug = args.slug or slugify(args.title)
    dest = ARTICLES / f"{slug}.md"
    if dest.exists():
        print(f"Ya existe {dest.relative_to(ROOT)}. Elija otro slug con --slug.", file=sys.stderr)
        return 1

    tpl = (TEMPLATES / tpl_name).read_text(encoding="utf-8")
    # sustituir el front matter de la plantilla por los datos reales
    front = (
        "---\n"
        f'title: "{args.title}"\n'
        f"author: {args.author}\n"
        f"date: {args.date}\n"
        f"format: {fmt}\n"
        "genres:\n"
        f'  - "{genre}"\n'
        f"lang: {args.lang}\n"
        "---\n"
    )
    body = re.sub(r"^---\n.*?\n---\n", "", tpl, count=1, flags=re.DOTALL)
    # sustituir el título de ejemplo del cuerpo por el real
    body = re.sub(r"^# .*$", f"# {args.title}", body, count=1, flags=re.MULTILINE)
    dest.write_text(front + body, encoding="utf-8")

    # registrar al principio de articles.json (más reciente primero)
    manifest = json.loads(DATA.read_text(encoding="utf-8"))
    lst = manifest.get("articles", [])
    if slug not in lst:
        lst.insert(0, slug)
    manifest["articles"] = lst
    DATA.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✓ Creado  {dest.relative_to(ROOT)}")
    print(f"✓ Registrado en {DATA.relative_to(ROOT)} (slug: {slug})")
    print("\nEdita el archivo y previsualiza con:  python3 -m http.server 8000")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
