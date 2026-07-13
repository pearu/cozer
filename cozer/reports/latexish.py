"""Convert the LaTeX-flavored text stored in legacy .coz files to an HTML
fragment for display.

Legacy events were authored for a LaTeX backend, so free-text fields (names,
notes, rule paragraphs, titles) may contain LaTeX. We decode:

- accent / ligature commands that occur in names, e.g. ``\\v{c}`` -> ``č``;
- ``\\\\`` -> line break (``<br>``);
- ``_`` / ``^`` -> subscript / superscript (``313.04_4`` -> ``313.04<sub>4</sub>``),
  with ``_{...}`` / ``^{...}`` grouped;
- ``~`` -> non-breaking space; grouping braces are stripped;
- ``--``/``---`` -> en/em dash.

A single ``\\`` always starts a command. Unknown commands are dropped; an accent
over an unmapped letter falls back to the bare letter. Literal text is
HTML-escaped, so the result is safe to embed directly.
"""

_ACCENT_LETTER = {
    "v": {"c": "č", "s": "š", "z": "ž", "r": "ř", "e": "ě", "n": "ň", "d": "ď",
          "t": "ť", "l": "ľ", "C": "Č", "S": "Š", "Z": "Ž", "R": "Ř", "N": "Ň", "E": "Ě"},
    "c": {"c": "ç", "C": "Ç", "s": "ş", "S": "Ş", "g": "ģ", "k": "ķ", "l": "ļ",
          "n": "ņ", "r": "ŗ", "t": "ţ"},
    "u": {"a": "ă", "g": "ğ", "A": "Ă", "G": "Ğ", "e": "ĕ", "i": "ĭ", "o": "ŏ", "u": "ŭ"},
    "H": {"o": "ő", "u": "ű", "O": "Ő", "U": "Ű"},
    "r": {"a": "å", "u": "ů", "A": "Å", "U": "Ů"},
}
_ACCENT_SYMBOL = {
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "y": "ý", "c": "ć",
          "s": "ś", "n": "ń", "z": "ź", "l": "ĺ", "r": "ŕ", "A": "Á", "E": "É",
          "I": "Í", "O": "Ó", "U": "Ú", "Y": "Ý", "C": "Ć", "S": "Ś", "N": "Ń", "Z": "Ź"},
    '"': {"a": "ä", "o": "ö", "u": "ü", "e": "ë", "i": "ï", "y": "ÿ",
          "A": "Ä", "O": "Ö", "U": "Ü", "E": "Ë"},
    "`": {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù", "A": "À", "E": "È", "O": "Ò"},
    "~": {"n": "ñ", "a": "ã", "o": "õ", "N": "Ñ", "A": "Ã", "O": "Õ"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û", "A": "Â", "E": "Ê", "O": "Ô"},
    "=": {"a": "ā", "e": "ē", "i": "ī", "o": "ō", "u": "ū", "A": "Ā", "O": "Ō", "U": "Ū"},
    ".": {"z": "ż", "Z": "Ż", "e": "ė", "E": "Ė", "c": "ċ"},
}
_NAMED = {"ss": "ß", "o": "ø", "O": "Ø", "aa": "å", "AA": "Å", "ae": "æ", "AE": "Æ",
          "l": "ł", "L": "Ł", "i": "ı", "j": "ȷ", "oe": "œ", "OE": "Œ",
          "th": "þ", "TH": "Þ", "dh": "ð", "DH": "Ð"}
_ESCAPED = set("&%$#_{}")


def _esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _read_arg(s, i):
    n = len(s)
    if i < n and s[i] == "{":
        k = s.find("}", i + 1)
        if k == -1:
            return s[i + 1:], n
        return s[i + 1:k], k + 1
    if i < n:
        return s[i], i + 1
    return "", i


def latex_to_html(s):
    s = str(s)
    out = []          # HTML pieces (markup appended raw)
    buf = []          # pending literal text (escaped on flush)

    def flush():
        if buf:
            out.append(_esc("".join(buf)))
            del buf[:]

    i, n = 0, len(s)
    while i < n:
        c = s[i]
        if c == "\\":
            i += 1
            if i >= n:
                break
            nc = s[i]
            if nc == "\\":                       # line break
                flush(); out.append("<br>"); i += 1
            elif nc in " ,;:!":                  # spacing commands
                buf.append(" "); i += 1
            elif nc in _ESCAPED:                 # escaped special char
                buf.append(nc); i += 1
            elif nc in _ACCENT_SYMBOL:           # \'e  \"o  \~n ...
                i += 1
                arg, i = _read_arg(s, i)
                buf.append(_ACCENT_SYMBOL[nc].get(arg, arg))
            elif nc.isalpha():                   # named control word
                j = i
                while j < n and s[j].isalpha():
                    j += 1
                cmd, i = s[i:j], j
                if i < n and s[i] == " ":        # control words gobble one space
                    i += 1
                if cmd in _ACCENT_LETTER:
                    arg, i = _read_arg(s, i)
                    buf.append(_ACCENT_LETTER[cmd].get(arg, arg))
                elif cmd in _NAMED:
                    buf.append(_NAMED[cmd])
                # else: unknown command -> dropped
            else:                                # \- \/ etc: drop backslash, keep char
                buf.append(nc); i += 1
        elif c == "_":                           # subscript
            i += 1
            arg, i = _read_arg(s, i)
            flush(); out.append("<sub>%s</sub>" % _esc(arg))
        elif c == "^":                           # superscript
            i += 1
            arg, i = _read_arg(s, i)
            flush(); out.append("<sup>%s</sup>" % _esc(arg))
        elif c == "~":
            buf.append(" "); i += 1
        elif c in "{}":
            i += 1                               # strip grouping braces
        elif s[i:i + 3] == "---":
            buf.append("—"); i += 3
        elif s[i:i + 2] == "--":
            buf.append("–"); i += 2
        else:
            buf.append(c); i += 1
    flush()
    return "".join(out)
