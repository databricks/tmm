"""Lab-guide app — one per workspace, deployed by agent_apps_setup as the privileged user and
granted CAN_USE to all students. Serves two self-contained HTML files baked at build time:

- GET /      -> guide.html  (the written participant guide, screenshots inlined)
- GET /deck  -> deck.html   (the field-guide slide deck; arrow keys to navigate)

No data access, no OBO, no scopes — static content only.
"""
import pathlib

from fastapi import FastAPI
from fastapi.responses import FileResponse

HERE = pathlib.Path(__file__).resolve().parent
app = FastAPI(title="Agent Apps Lab — Guide")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/")
def guide() -> FileResponse:
    return FileResponse(HERE / "guide.html", media_type="text/html")


@app.get("/deck")
def deck() -> FileResponse:
    return FileResponse(HERE / "deck.html", media_type="text/html")
