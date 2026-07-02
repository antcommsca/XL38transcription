#!/usr/bin/env python3
"""
page2tei.py — converte PAGE XML (Transkribus) in TEI.

Ogni file PAGE XML (una facciata/pagina) diventa un <div type="page">.
Ogni TextRegion diventa un <div> figlio (con eventuali metadati da
'structure' come attributi). Ogni TextLine diventa un <l>.

Le annotazioni codificate nell'attributo @custom di TextLine (nota,
unclear, gap, abbrev) vengono risolte come markup inline sul testo,
usando gli offset/length per individuare la porzione di stringa
interessata. Nessuna coordinata (Coords/Baseline) viene riportata.

Uso:
    python3 page2tei.py file1.xml file2.xml ... > out.tei.xml
    python3 page2tei.py --glob "export_job_*/*/page/*.xml" > out.tei.xml

Solo libreria standard.
"""

import argparse
import glob
import re
import sys
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

NS = {"p": "http://schema.primaresearch.org/PAGE/gts/pagecontent/2013-07-15"}

# ---------------------------------------------------------------------------
# Parsing del 'custom' attribute di Transkribus
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"(\w+)\s*\{([^}]*)\}")
_UESC_RE = re.compile(r"\\u([0-9a-fA-F]{4})")


def decode_escapes(value: str) -> str:
    """Decodifica sequenze tipo \\u0020 (usate da Transkribus per spazi/virgole
    dentro i valori, dato che ';' e ':' sono delimitatori del formato)."""
    return _UESC_RE.sub(lambda m: chr(int(m.group(1), 16)), value)


def parse_custom(custom_str: str) -> dict:
    """Ritorna {tagname: [ {param: value, ...}, ... ]} — lista perché uno
    stesso tag (es. 'unclear', 'gap') può comparire più volte nella stringa."""
    result: dict = {}
    if not custom_str:
        return result
    for tag, body in _TAG_RE.findall(custom_str):
        params = {}
        for pair in body.split(";"):
            pair = pair.strip()
            if not pair or ":" not in pair:
                continue
            k, v = pair.split(":", 1)
            params[k.strip()] = decode_escapes(v.strip())
        result.setdefault(tag, []).append(params)
    return result


def first(custom: dict, tag: str) -> dict:
    vals = custom.get(tag)
    return vals[0] if vals else {}


# ---------------------------------------------------------------------------
# Markup inline della riga di testo
# ---------------------------------------------------------------------------

SPAN_TAGS = ("nota", "unclear", "gap", "abbrev")


def build_line_content(text: str, custom: dict) -> str:
    spans = []
    for kind in SPAN_TAGS:
        for params in custom.get(kind, []):
            if "offset" not in params:
                continue
            offset = int(params["offset"])
            length = int(params.get("length", 0))
            spans.append((offset, length, kind, params))

    # Ordine: per offset crescente; a parità di offset, prima gli span con
    # lunghezza > 0 (occupano testo), poi i marcatori puntuali (length 0).
    # Decisione arbitraria per gestire annotazioni sovrapposte sullo stesso
    # offset (vedi nota nella risposta) — verificare caso per caso.
    spans.sort(key=lambda s: (s[0], 0 if s[1] > 0 else 1))

    pieces = []
    cursor = 0
    for offset, length, kind, params in spans:
        if offset < cursor:
            # annotazione che punta a una posizione già "consumata" da uno
            # span precedente con lo stesso offset: la trattiamo come
            # marcatore puntuale nella posizione corrente.
            offset = cursor

        if offset > cursor:
            pieces.append(escape(text[cursor:offset]))
            cursor = offset

        if length > 0:
            span_text = escape(text[offset:offset + length])
            if kind == "unclear":
                attrs = []
                if "reason" in params:
                    attrs.append('reason="%s"' % escape(params["reason"].lower()))
                if "agent" in params:
                    attrs.append('resp="%s"' % escape(params["agent"]))
                if params.get("continued") == "true":
                    attrs.append('next="#cont"')
                a = (" " + " ".join(attrs)) if attrs else ""
                pieces.append(f"<unclear{a}>{span_text}</unclear>")
            elif kind == "nota":
                note_text = escape(params.get("nota", ""))
                pieces.append(f'<seg type="nota">{span_text}</seg><note>{note_text}</note>')
            elif kind == "abbrev":
                expan = escape(params.get("expansion", ""))
                pieces.append(f"<choice><abbr>{span_text}</abbr><expan>{expan}</expan></choice>")
            elif kind == "gap":
                # non atteso nei dati osservati (length sempre 0), gestito
                # per robustezza: il contenuto trascritto diventa <supplied>
                reason = params.get("reason", "").lower()
                pieces.append(f'<supplied reason="{escape(reason)}">{span_text}</supplied>')
            cursor = offset + length
        else:
            if kind == "gap":
                attrs = []
                mapping = [("unit", "unit"), ("quantity", "quantity"),
                           ("agent", "resp"), ("reason", "reason")]
                for src, tei in mapping:
                    if src in params:
                        v = params[src].lower() if tei == "reason" else params[src]
                        attrs.append(f'{tei}="{escape(v)}"')
                # attributi non-standard TEI, mantenuti per non perdere info
                for extra in ("supplied", "atleast", "atmost", "nota"):
                    for k in params:
                        if k.lower() == extra:
                            attrs.append(f'{extra}="{escape(params[k])}"')
                a = (" " + " ".join(attrs)) if attrs else ""
                pieces.append(f"<gap{a}/>")
            elif kind == "nota":
                pieces.append(f'<note>{escape(params.get("nota", ""))}</note>')
            elif kind == "unclear":
                pieces.append("<unclear/>")
            elif kind == "abbrev":
                pass  # length 0 non ha senso per un'abbreviazione, ignorato

    if cursor < len(text):
        pieces.append(escape(text[cursor:]))
    return "".join(pieces)


# ---------------------------------------------------------------------------
# Conversione di un file PAGE XML in un <div type="page">
# ---------------------------------------------------------------------------

def convert_file(path: str) -> str:
    tree = ET.parse(path)
    root = tree.getroot()
    page = root.find("p:Page", NS)
    if page is None:
        raise ValueError(f"{path}: elemento <Page> non trovato")

    image_filename = page.get("imageFilename", "")
    page_id = re.sub(r"\.[A-Za-z0-9]+$", "", image_filename) or "page"

    out = [f'<div type="page" xml:id="{escape(page_id)}" facs="{escape(image_filename)}">']

    for region in page.findall("p:TextRegion", NS):
        rcustom = parse_custom(region.get("custom", ""))
        ro = first(rcustom, "readingOrder")
        struct = first(rcustom, "structure")

        rattrs = [f'xml:id="{escape(region.get("id", ""))}"']
        if "index" in ro:
            rattrs.append(f'n="{escape(ro["index"])}"')
        rattrs.append(f'type="{escape(struct.get("type", "text"))}"')
        if "title" in struct:
            rattrs.append(f'source="{escape(struct["title"])}"')
        if "book" in struct:
            rattrs.append(f'book="{escape(struct["book"])}"')
        if "verses" in struct:
            rattrs.append(f'verses="{escape(struct["verses"])}"')

        out.append(f'  <div {" ".join(rattrs)}>')

        for line in region.findall("p:TextLine", NS):
            lcustom = parse_custom(line.get("custom", ""))
            ro_l = first(lcustom, "readingOrder")
            struct_l = first(lcustom, "structure")

            unicode_el = line.find("p:TextEquiv/p:Unicode", NS)
            text = unicode_el.text if unicode_el is not None and unicode_el.text else ""

            lattrs = [f'xml:id="{escape(line.get("id", ""))}"']
            if "index" in ro_l:
                lattrs.append(f'n="{escape(ro_l["index"])}"')
            if "type" in struct_l:
                lattrs.append(f'type="{escape(struct_l["type"])}"')

            content = build_line_content(text, lcustom)
            out.append(f'    <l {" ".join(lattrs)}>{content}</l>')

        out.append("  </div>")

    out.append("</div>")
    return "\n".join(out)


TEI_HEADER = """<teiHeader>
  <fileDesc>
    <titleStmt>
      <title>Trascrizione diplomatica (da PAGE XML / Transkribus)</title>
    </titleStmt>
    <publicationStmt>
      <p>Generato automaticamente da page2tei.py — da rivedere editorialmente.</p>
    </publicationStmt>
    <sourceDesc>
      <p>Fonte: export PAGE XML Transkribus.</p>
    </sourceDesc>
  </fileDesc>
</teiHeader>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="File PAGE XML da convertire")
    ap.add_argument("--glob", dest="pattern", help="Pattern glob (ricorsivo con **)")
    ap.add_argument("-o", "--output", help="File di output (default: stdout)")
    args = ap.parse_args()

    paths = list(args.files)
    if args.pattern:
        paths.extend(sorted(glob.glob(args.pattern, recursive=True)))
    if not paths:
        ap.error("nessun file specificato (usa argomenti posizionali o --glob)")

    page_divs = []
    for p in paths:
        try:
            page_divs.append(convert_file(p))
        except Exception as exc:
            print(f"[WARN] {p}: {exc}", file=sys.stderr)

    body = "\n".join(page_divs)
    tei = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TEI xmlns="http://www.tei-c.org/ns/1.0">\n'
        f"{TEI_HEADER}\n"
        "<text>\n<body>\n"
        f"{body}\n"
        "</body>\n</text>\n</TEI>\n"
    )

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(tei)
    else:
        sys.stdout.write(tei)


if __name__ == "__main__":
    main()
