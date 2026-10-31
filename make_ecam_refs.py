# -*- coding: utf-8 -*-
"""Convert references.bib (Elsevier Harvard, Safety Science) into
Emerald Harvard (Engineering, Construction and Architectural Management, ECAM).

Emerald Harvard target form
---------------------------
Journal article:
  Surname, I., Surname, I. and Surname, I. (Year), "Title of article",
  *Journal Name*, Vol. X No. Y, pp. a-b.

Book:
  Surname, I. (Year), *Title of Book*, Publisher, Place.

Working paper / report:
  Organisation (Year), *Title*, Report number, Publisher, Place.

Software / online:
  Surname, I. (Year), "Title", available at: URL
"""
import io
import re

SRC = "references.bib"
OUT = "references_ECAM_Harvard.md"

# ---------------------------------------------------------------- parsing


def strip_braces(s: str) -> str:
    s = re.sub(r"\\url\{([^}]*)\}", r"\1", s)
    s = re.sub(r"\\[a-zA-Z]+\s*", "", s)
    s = s.replace("{", "").replace("}", "")
    s = s.replace("\\'e", "é").replace('\\"e', "ë").replace("\\'E", "É")
    s = re.sub(r"--", "–", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def split_fields(body: str):
    """Return dict of bibtex fields from the inside of an entry."""
    fields, buf, depth = {}, "", 0
    for ch in body:
        if ch == "{":
            depth += 1
            if depth == 1:
                continue
        elif ch == "}":
            depth -= 1
            if depth == 0:
                continue
        if depth == 0 and ch == ",":
            _commit(fields, buf)
            buf = ""
            continue
        buf += ch
    _commit(fields, buf)
    return fields


def _commit(fields, buf):
    if "=" in buf:
        k, v = buf.split("=", 1)
        k = k.strip().lower()
        if k:
            fields[k] = v.strip()


def parse_bib(text: str):
    entries = []
    for m in re.finditer(r"@(\w+)\{([^,]+),", text):
        etype, key = m.group(1).lower(), m.group(2).strip()
        start = m.end()
        depth, i = 1, m.end()
        while i < len(text) and depth > 0:
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
            i += 1
        body = text[start:i - 1]
        entries.append((etype, key, split_fields(body)))
    return entries


# ---------------------------------------------------------------- authors

PARTICLES = {"van", "von", "de", "der", "den", "del", "della", "di", "da", "la", "le"}


def initials(given: str) -> str:
    """'Charles R.' -> 'C.R.' ; 'Patrick X.W.' -> 'P.X.W.'"""
    given = strip_braces(given)
    out = []
    for tok in re.split(r"[\s\-\.]+", given):
        tok = tok.strip(".")
        if not tok:
            continue
        if tok.lower() in PARTICLES:
            continue
        out.append(tok[0].upper() + ".")
    return "".join(out)


def is_corporate(raw: str) -> bool:
    """A corporate author is wrapped in double braces: {{U.S. Bureau ...}}.
    parse_fields consumes the outer pair, so one brace is left."""
    return raw.strip().startswith("{")


def fmt_name(raw: str) -> str:
    raw = strip_braces(raw)
    if "," in raw:
        surname, given = raw.split(",", 1)
        return f"{surname.strip()}, {initials(given)}"
    parts = raw.split()
    return f"{parts[-1]}, {initials(' '.join(parts[:-1]))}"


def fmt_authors(raw: str, maxa: int = 6) -> str:
    if is_corporate(raw):
        name = strip_braces(raw)
        name = re.sub(r"^U\.S\.\s+", "", name)          # "U.S. Bureau of ..." -> "Bureau of ..."
        if name.startswith("Occupational Safety and Health Administration"):
            name += " (OSHA)"                            # in-text form is (OSHA, 2019)
        return name
    raw = strip_braces(raw)
    names = [n.strip() for n in re.split(r"\s+and\s+", raw) if n.strip()]
    truncated = False
    if any(n.lower() == "others" for n in names):
        names = [n for n in names if n.lower() != "others"]
        truncated = True
    if len(names) > maxa:
        names = names[:maxa]
        truncated = True
    names = [fmt_name(n) for n in names]
    if not names:
        return ""
    if truncated:
        return ", ".join(names) + " et al."
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + " and " + names[-1]


# ---------------------------------------------------------------- rendering

def dash_pages(p: str) -> str:
    p = strip_braces(p)
    return p.replace("–", "-")


def render(etype, f):
    au = fmt_authors(f.get("author", ""))
    yr = strip_braces(f.get("year", "n.d."))
    title = strip_braces(f.get("title", "")).rstrip(".")
    head = f"{au} ({yr}), " if au else f"{yr}, "

    if etype == "article":
        jr = strip_braces(f.get("journal", ""))
        vol = strip_braces(f.get("volume", "")).strip()
        num = strip_braces(f.get("number", "")).strip()
        pg = dash_pages(f.get("pages", ""))
        bits = []
        if vol and num:
            bits.append(f"Vol. {vol} No. {num}")
        elif vol:
            bits.append(f"Vol. {vol}")
        elif num:
            bits.append(f"No. {num}")
        if pg:
            if "-" in pg:
                bits.append(f"pp. {pg}")
            elif re.search(r"[A-Za-z]", pg):
                bits.append(pg)                      # Cochrane article id
            elif len(pg) >= 5:
                bits.append(f"article {pg}")         # continuous article number
            else:
                bits.append(f"p. {pg}")
        tail = ", ".join(bits)
        out = f'{head}"{title}", *{jr}*'
        if tail:
            out += f", {tail}"
        out += "."
        if f.get("doi"):
            out += f" doi: {strip_braces(f['doi'])}."
        return out

    if etype == "book":
        pub = strip_braces(f.get("publisher", ""))
        addr = strip_braces(f.get("address", ""))
        tail = ", ".join([x for x in (pub, addr) if x])
        return f"{head}*{title}*, {tail}." if tail else f"{head}*{title}*."

    if etype == "techreport":
        inst = strip_braces(f.get("institution", ""))
        num = strip_braces(f.get("number", ""))
        addr = strip_braces(f.get("address", ""))
        tail = ", ".join([x for x in (num, inst, addr) if x])
        return f"{head}*{title}*, {tail}."

    # misc / online
    url = strip_braces(f.get("howpublished", "")) or strip_braces(f.get("url", ""))
    out = f'{head}"{title}"'
    if url:
        out += f", available at: {url}"
    return out + "."


def main():
    text = io.open(SRC, encoding="utf-8").read()
    entries = parse_bib(text)
    rows = []
    for etype, key, f in entries:
        au = fmt_authors(f.get("author", ""))
        rows.append((au, strip_braces(f.get("year", "0")), key, render(etype, f)))

    def sortkey(r):
        # corporate authors sort on their first significant word
        a = r[0].lower().replace("{", "").replace("}", "")
        return (a, r[1], r[2])

    rows.sort(key=sortkey)

    lines = [
        "# References — Emerald Harvard (Engineering, Construction and Architectural Management)",
        "",
        "Generated from `references.bib` by `make_ecam_refs.py`. "
        f"{len(rows)} entries, alphabetical, no numbering.",
        "",
        "---",
        "",
    ]
    for _au, _yr, _key, s in rows:
        lines.append(s)
        lines.append("")

    io.open(OUT, "w", encoding="utf-8").write("\n".join(lines).rstrip() + "\n")
    print(f"wrote {OUT}: {len(rows)} entries")
    for _au, _yr, key, s in rows[:3]:
        print("  e.g.", s[:120])


if __name__ == "__main__":
    main()
