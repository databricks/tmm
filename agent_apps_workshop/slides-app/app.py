"""Lab-companion slides — static Databricks App, multi-deck edition.

Serves N style variations of the lab-companion deck from `decks/<slug>.html`
behind a small picker at GET /. No data access, no OBO, no scopes: every deck
is a self-contained HTML file, so the app needs nothing beyond the Apps
runtime itself.
"""
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse

HERE = pathlib.Path(__file__).resolve().parent
DECKS_DIR = HERE / "decks"

# Registry: slug -> (display name, one-line vibe). Order = picker order.
# A deck only shows on the picker once its file exists in decks/.
DECKS: dict[str, tuple[str, str]] = {
    "8-bit-orbit": ("8-Bit Orbit", "Deep cosmic navy, three neons, scanlines — the incumbent."),
    "pin-and-paper": ("Pin & Paper", "Corkboard field-notes: pinned cards, tape, handwritten energy."),
    "vellum": ("Vellum", "Warm parchment calm — soft, literary, low-noise."),
    "cobalt-grid": ("Cobalt Grid", "Engineered blueprint blue — crisp grid discipline."),
    "signal": ("Signal", "Institutional and trustworthy — the calm corporate pole."),
    "broadside": ("Broadside", "Dramatic dark editorial — big type, high contrast (wildcard)."),
}

app = FastAPI(title="Agent Apps Lab — Companion Slides")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
def picker() -> HTMLResponse:
    cards = []
    for slug, (name, vibe) in DECKS.items():
        if not (DECKS_DIR / f"{slug}.html").is_file():
            continue
        cards.append(
            f'<a class="card" href="/deck/{slug}">'
            f'<span class="swatch s-{slug}"></span>'
            f"<h2>{name}</h2><p>{vibe}</p></a>"
        )
    body = "\n".join(cards) or "<p class='empty'>No decks deployed yet.</p>"
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Lab Companion — pick a style</title>
<style>
  :root {{ color-scheme: dark; }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #101216; color: #e8e8ec; font: 16px/1.5 -apple-system, 'Helvetica Neue', sans-serif;
         min-height: 100vh; padding: 56px 24px; }}
  header {{ max-width: 960px; margin: 0 auto 36px; }}
  header h1 {{ font-size: 28px; letter-spacing: -0.01em; }}
  header p {{ color: #9aa0ab; margin-top: 6px; }}
  .grid {{ max-width: 960px; margin: 0 auto; display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }}
  .card {{ display: block; background: #181b22; border: 1px solid #262b35; border-radius: 10px;
          padding: 20px; text-decoration: none; color: inherit;
          transition: border-color .15s, transform .15s; }}
  .card:hover {{ border-color: #4a90d9; transform: translateY(-2px); }}
  .card h2 {{ font-size: 18px; margin: 12px 0 4px; }}
  .card p {{ font-size: 13.5px; color: #9aa0ab; }}
  .swatch {{ display: block; height: 56px; border-radius: 6px; }}
  .s-8-bit-orbit {{ background: linear-gradient(120deg, #0A0E27 55%, #5EDCF4 55% 70%, #F0A6CA 70% 85%, #F4D03F 85%); }}
  .s-pin-and-paper {{ background: linear-gradient(120deg, #b08968 50%, #f5ebe0 50% 80%, #d62828 80%); }}
  .s-vellum {{ background: linear-gradient(120deg, #f3ead8 60%, #c9b48a 60% 85%, #7a5c2e 85%); }}
  .s-cobalt-grid {{ background: linear-gradient(120deg, #0a2472 60%, #1e6fd9 60% 85%, #e8f1ff 85%); }}
  .s-signal {{ background: linear-gradient(120deg, #11304d 60%, #2f6f8f 60% 85%, #e6eef2 85%); }}
  .s-broadside {{ background: linear-gradient(120deg, #111 60%, #e8e3d8 60% 85%, #c8102e 85%); }}
  .empty {{ color: #9aa0ab; }}
</style></head>
<body>
<header>
  <h1>Lab Companion — pick a style</h1>
  <p>Same 8 slides, different design systems. Arrow keys / space to navigate inside a deck.</p>
</header>
<div class="grid">
{body}
</div>
</body></html>"""
    return HTMLResponse(html)


@app.get("/deck/{slug}")
def deck(slug: str):
    path = DECKS_DIR / f"{slug}.html"
    if slug not in DECKS or not path.is_file():
        return RedirectResponse(url="/", status_code=302)
    return FileResponse(path, media_type="text/html")
