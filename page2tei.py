#!/usr/bin/env python3
"""
page2tei.py — converte PAGE XML (Transkribus) in TEI.

Ogni file PAGE XML (una facciata/pagina) diventa un <div type="page">.
Ogni TextRegion diventa un <div> figlio (con eventuali metadati da
'structure' come attributi). Ogni TextLine diventa un <l>.

Le annotazioni codificate nell'attributo @custom di TextLine (nota,
unclear, gap/supplied, abbrev, add, corr, del) vengono risolte come
markup inline sul testo, usando gli offset/length per individuare la
porzione di stringa interessata. Nessuna coordinata (Coords/Baseline)
viene riportata.

Mapping tag Transkribus -> TEI (concordato con biblioteca/collega,
vedi TAG-TEI.pdf):
  abbrev  (expansion)          -> <choice><abbr/><expan/></choice>
  add     (place)               -> <add place="...">
  corr    (original)            -> <subst><add/><del/></subst>
  del     ()                    -> <del>
  gap     (reason, supplied)    -> <supplied reason="..." source="#geymonat_2008">
                                    (il contenuto e' il valore della chiave
                                    'supplied', NON una porzione del testo
                                    trascritto: length e' sempre 0)
  unclear (reason, agent[, alternative]) -> <unclear reason="...">
                                    reason = agent se presente, altrimenti
                                    reason (scelta del collega); se e'
                                    presente 'alternative', le due letture
                                    vengono avvolte in <choice>.

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

# Fonte fissa per il testo supplito, concordata via TAG-TEI.pdf.
SUPPLIED_SOURCE = "#geymonat_2008"

# Tag che avvolgono una porzione (offset/length) del testo trascritto.
SPAN_TAGS = ("nota", "unclear", "abbrev", "add", "corr", "del")
# Tag il cui contenuto NON viene dalla trascrizione ma da una proprietà
# (length e' sempre 0: non c'e' nulla da "consumare" nel testo trascritto).
PROPERTY_TAGS = ("gap",)


def _unclear_reason(params: dict) -> str:
    """Il collega ha chiesto di collassare agent+reason in un solo
    attributo @reason, preferendo il valore di 'agent' quando presente."""
    if "agent" in params:
        return params["agent"].lower()
    return params.get("reason", "").lower()


def build_line_content(text: str, custom: dict) -> str:
    spans = []
    for kind in SPAN_TAGS + PROPERTY_TAGS:
        for params in custom.get(kind, []):
            if "offset" not in params:
                continue
            offset = int(params["offset"])
            length = int(params.get("length", 0))
            spans.append((offset, length, kind, params))

    # Ordine: per offset crescente; a parità di offset, prima gli span con
    # lunghezza > 0 (occupano testo), poi i marcatori puntuali (length 0,
    # es. 'gap'/'supplied'). Decisione arbitraria per gestire annotazioni
    # sovrapposte sullo stesso offset — verificare caso per caso.
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

        if kind in PROPERTY_TAGS:
            # 'gap': se e' presente una lettura congetturale (chiave
            # 'supplied' non vuota) -> TEI <supplied> con quel testo come
            # contenuto (non e' una fetta del testo trascritto: la lettera
            # non c'e' piu'). Se non c'e' alcuna lettura proposta -> TEI
            # <gap> "puro" (quantity/unit/reason sono attributi TEI
            # standard per lacune non risolte).
            if kind == "gap":
                supplied_val = params.get("supplied", "")
                reason = params.get("reason", "").lower()
                if supplied_val:
                    r = f' reason="{escape(reason)}"' if reason else ""
                    pieces.append(
                        f'<supplied{r} source="{SUPPLIED_SOURCE}">{escape(supplied_val)}</supplied>'
                    )
                else:
                    attrs = []
                    if reason:
                        attrs.append(f'reason="{escape(reason)}"')
                    if "quantity" in params:
                        attrs.append(f'quantity="{escape(params["quantity"])}"')
                    if "unit" in params:
                        attrs.append(f'unit="{escape(params["unit"].lower())}"')
                    if "atLeast" in params:
                        attrs.append(f'atLeast="{escape(params["atLeast"])}"')
                    if "atMost" in params:
                        attrs.append(f'atMost="{escape(params["atMost"])}"')
                    a = (" " + " ".join(attrs)) if attrs else ""
                    pieces.append(f"<gap{a}/>")
            continue  # non avanza cursor: length e' 0 per definizione

        if length > 0:
            span_text = escape(text[offset:offset + length])
            if kind == "unclear":
                reason = _unclear_reason(params)
                r = f' reason="{escape(reason)}"' if reason else ""
                if "alternative" in params:
                    alt = escape(params["alternative"])
                    pieces.append(
                        f'<choice><unclear{r}>{span_text}</unclear>'
                        f'<unclear{r}>{alt}</unclear></choice>'
                    )
                else:
                    pieces.append(f"<unclear{r}>{span_text}</unclear>")
            elif kind == "nota":
                note_text = escape(params.get("nota", ""))
                pieces.append(f'<seg type="nota">{span_text}</seg><note>{note_text}</note>')
            elif kind == "abbrev":
                expan = escape(params.get("expansion", ""))
                pieces.append(f"<choice><abbr>{span_text}</abbr><expan>{expan}</expan></choice>")
            elif kind == "add":
                place = escape(params.get("place", ""))
                p = f' place="{place}"' if place else ""
                pieces.append(f"<add{p}>{span_text}</add>")
            elif kind == "corr":
                original = escape(params.get("original", ""))
                pieces.append(f"<subst><add>{span_text}</add><del>{original}</del></subst>")
            elif kind == "del":
                pieces.append(f"<del>{span_text}</del>")
            cursor = offset + length
        else:
            # marcatore puntuale (length 0) per un tag che normalmente
            # avvolge testo: non dovrebbe capitare nei dati osservati,
            # gestito per robustezza senza perdere l'informazione.
            if kind == "nota":
                pieces.append(f'<note>{escape(params.get("nota", ""))}</note>')
            elif kind == "unclear":
                pieces.append(f'<unclear reason="{escape(_unclear_reason(params))}"/>')
            # abbrev/add/corr/del a lunghezza 0 non hanno senso: ignorati

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
      <!-- TODO: inserire qui la biblStruct per 'geymonat_2008'
           (xml:id="geymonat_2008"), referenziata da @source su
           tutti gli elementi <supplied>. File non ancora ricevuto. -->
    </sourceDesc>
  </fileDesc>
</teiHeader>"""


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("files", nargs="*", help="File PAGE XML da convertire")
    ap.add_argument("--glob", dest="pattern", help="Pattern glob (ricorsivo con **)")
    ap.add_argument("--header", help="File contenente il <teiHeader> da usare "
                                      "(default: header minimo generato automaticamente)")
    ap.add_argument("-o", "--output", default="XL38transcription.tei.xml",
                     help="File di output (default: XL38transcription.tei.xml)")
    args = ap.parse_args()

    paths = list(args.files)
    if args.pattern:
        matched = sorted(glob.glob(args.pattern, recursive=True))
        if not matched:
            ap.error(f"--glob '{args.pattern}' non ha trovato alcun file "
                      f"(verifica la profondità delle directory)")
        paths.extend(matched)
    if not paths:
        ap.error("nessun file specificato (usa argomenti posizionali o --glob)")

    if args.header:
        with open(args.header, "r", encoding="utf-8") as f:
            header = f.read().strip()
        try:
            ET.fromstring(header)
        except ET.ParseError as exc:
            ap.error(f"--header '{args.header}' non è XML ben formato: {exc}")
    else:
        header = TEI_HEADER
        print("[WARN] nessun --header specificato, uso header minimo di fallback",
              file=sys.stderr)

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
        f"{header}\n"
        "<text>\n<body>\n"
        f"{body}\n"
        "</body>\n</text>\n</TEI>\n"
    )

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(tei)
    print(f"Scritto: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
