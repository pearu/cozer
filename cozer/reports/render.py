"""Offline HTML/CSS -> PDF rendering for cozer reports (WeasyPrint).

Per-report page orientation and running footers are supplied via ``page_css``;
the shared table styling is ``TABLE_CSS``.
"""
import weasyprint

TABLE_CSS = """
body { font-family: "DejaVu Sans", Helvetica, Arial, sans-serif; color:#111; font-size:9pt; }
h1.event-title { font-size:13pt; margin:0 0 .1cm 0; }
.event-meta { font-size:9pt; color:#333; margin:0 0 .35cm 0; }
h2.report-heading { text-align:center; font-size:14pt; margin:.1cm 0 .45cm 0; }
h3.class-heading { font-size:11pt; margin:.55cm 0 .15cm 0; padding-bottom:1px;
                   border-bottom:1.5px solid #000; }
/* table-layout:fixed + a colgroup summing to 100% keeps every table within the
   page width; long cells wrap instead of overflowing. */
table.results { border-collapse:collapse; width:100%; table-layout:fixed; margin:0 0 .1cm 0; }
table.results thead { display:table-header-group; }   /* repeat header across page breaks */
/* No mid-word breaking, so numbers are never split; result cells carry an
   explicit zero-width break after each "/" (see final._result_text). */
table.results th, table.results td { border:1px solid #555; padding:2px 3px; vertical-align:top; }
table.results th { background:#e8e8e8; font-weight:bold; text-align:center; }
table.results td.num, table.results th.num { text-align:center; }
table.results td.name { text-align:left; overflow-wrap:break-word; }   /* only long names may break */
table.results tr.sub td { color:#333; border-top:none; font-style:italic; }
table.results .summary { background:#f2f2f2; font-weight:bold; }
.legend { font-size:8pt; color:#333; margin:.05cm 0 .25cm 0; }
sup { font-size:70%; }
"""


def _css_str(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"')


def page_css(orientation, footer_left="", footer_center="", footer_right=""):
    return (
        '@page { size: A4 %s; margin: 1.3cm 1.1cm 1.7cm 1.1cm;'
        ' @bottom-left { content: "%s"; font-size:8pt; color:#333; }'
        ' @bottom-center { content: "%s" " " counter(page); font-size:8pt; color:#333; }'
        ' @bottom-right { content: "%s"; font-size:8pt; color:#333; } }'
        % (orientation, _css_str(footer_left), _css_str(footer_center), _css_str(footer_right))
    )


def render_pdf(html, out_path):
    weasyprint.HTML(string=html).write_pdf(out_path)


def render_pdf_bytes(html):
    return weasyprint.HTML(string=html).write_pdf()
