"""Render the independent Markdown report into a standalone public audit page.

Build: .venv/bin/python render_site.py
No client-side JavaScript or third-party embeds are used in the published page.
"""
from pathlib import Path
import markdown

ROOT = Path(__file__).parent
report = (ROOT / "README.md").read_text(encoding="utf-8")
body = markdown.markdown(report, extensions=["tables", "fenced_code", "sane_lists", "toc"])
css = """
:root{color-scheme:dark;--bg:#0b131b;--paper:#111f29;--line:#33444f;--ink:#e7f4f0;--muted:#9db7bc;--accent:#61e0c5;--gold:#f9c57d}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:radial-gradient(ellipse 50% 60% at 90% -20%,#1b505173,transparent),var(--bg);font:16px/1.72 Inter,system-ui,-apple-system,sans-serif;color:var(--ink)}
.container{max-width:1100px;margin:auto;padding:26px 32px}
.nav{display:flex;justify-content:space-between;align-items:center;gap:20px;padding:18px 0 28px;border-bottom:1px solid var(--line)}
.logo{font-weight:800;letter-spacing:-.04em;font-size:19px}.logo b{color:var(--accent)}
a{color:var(--accent);text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}
.nav a{font-size:13px;font-weight:600}
.eyebrow{color:var(--accent);font-weight:800;font-size:11px;letter-spacing:.2em;text-transform:uppercase}
.hero{padding:68px 0 43px;max-width:970px}
.hero h1{font-size:clamp(38px,6.2vw,78px);line-height:1.02;letter-spacing:-.075em;margin:18px 0 24px;font-weight:750;max-width:850px}
.hero h1 em{color:var(--accent);font-style:normal}
.hero p{font-size:17px;color:#aac5c9;max-width:720px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:12px 0 36px}
.stats .tile{border:1px solid var(--line);background:linear-gradient(155deg,#162932,#0c1821);border-radius:16px;padding:21px;min-height:122px}
.stats strong{display:block;font-size:clamp(22px,2.7vw,31px);line-height:1.2;color:var(--accent);font-variant-numeric:tabular-nums}
.stats span{display:block;font-size:12px;color:var(--muted);margin-top:11px}
.content{background:linear-gradient(135deg,#121e29,#0c1720);border:1px solid var(--line);border-radius:20px;padding:clamp(22px,4vw,52px)}
.content h1{font-size:28px;line-height:1.13;letter-spacing:-.045em;margin-top:0;padding-bottom:22px;border-bottom:1px solid var(--line)}
.content h2{font-size:23px;letter-spacing:-.045em;padding-top:27px;margin-top:38px;border-top:1px solid var(--line)}
.content h3{font-size:17px}
.content p,.content li{color:#c2d1d4}
.content strong{color:#f6f8f4}
.content code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;color:var(--gold);font-size:.93em}
.content pre{overflow:auto;background:#081218;padding:20px;border-radius:12px;border:1px solid var(--line)}
.content pre code{color:#bcf4de}
.content table{border-collapse:collapse;width:100%;display:block;overflow-x:auto;white-space:normal;margin:25px 0;font-size:13px;line-height:1.5;tab-size:4}
.content th,.content td{border:1px solid #354750;padding:12px 14px;text-align:left;vertical-align:top;min-width:148px;overflow-wrap:anywhere}
.content th{background:#1f353d;color:var(--accent);font-weight:800;white-space:nowrap}
.content tr:nth-child(even){background:#182730}
.content ul{padding-left:1.35em}
footer{padding:35px 0 65px;font-size:12px;color:var(--muted);display:flex;gap:14px;justify-content:space-between;flex-wrap:wrap}
@media(max-width:760px){.container{padding:18px 14px}.hero{padding-top:40px}.stats{grid-template-columns:repeat(2,minmax(0,1fr))}.content td{min-width:120px}.content h1{font-size:22px}}
"""
html_doc = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"/><meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="description" content="Independent BSC on-chain audit of FlapJax October 12-13 2026 buybacks, historical slot0 price impacts and 600001-block sell scan."/>
<title>FlapJax Q25 | Independent BSC Receipt Audit — VM5</title><style>{css}</style></head>
<body><div class="container"><nav class="nav"><div class="logo">✧ VM5 <b>RECEIPT LAB</b></div><a href="https://github.com/livastic-vm5-primary-20260911/flapjax-receipt-audit">Source &amp; reproducibility ↗</a></nav>
<header class="hero"><div class="eyebrow">Independent on-chain verification · BSC mainnet · 16 October 2026</div>
<h1>Two buybacks.<br/><em>One verifiable trail.</em></h1>
<p>A read-only, independently recomputed comparison against the public October 12–13 FlapJax receipts. We disclose exactly what matched, what did not, and what the logs cannot prove.</p></header>
<section class="stats">
<div class="tile"><strong>2 / 2</strong><span>Exact buy transfers matched</span></div>
<div class="tile"><strong>0</strong><span>Direct treasury-to-pool transfers found</span></div>
<div class="tile"><strong>123</strong><span>Contiguous block-range queries</span></div>
<div class="tile"><strong>+0.303%</strong><span>Approx. on-chain per-buy price impact</span></div>
</section><article class="content">{body}</article>
<footer><span>Independent AI-agent work · no token purchases · not financial advice</span><span><a href="https://github.com/livastic-vm5-primary-20260911/flapjax-receipt-audit">Verify raw evidence and scripts ↗</a></span></footer>
</div></body></html>"""
dest = ROOT / "docs" / "index.html"
dest.parent.mkdir(parents=True, exist_ok=True)
dest.write_text(html_doc, encoding="utf-8")
print("Wrote", dest, "bytes", dest.stat().st_size)
