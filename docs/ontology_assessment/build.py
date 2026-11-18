"""Build the standalone ontology assessment page.

Embeds the packaged ontology JSON files and app.js into template.html and
writes ontology_assessment.html alongside it. Run after the JSON files change:

    python docs/ontology_assessment/build.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
ONTOLOGY = HERE.parent.parent / "acro"
NAMES = ("analyses", "statbarns", "risks", "checks")


def main() -> None:
    """Generate the single-file HTML page."""
    data = {n: json.loads((ONTOLOGY / f"{n}.json").read_text("utf-8")) for n in NAMES}
    # Escape "<" so definitions can never close the surrounding script tag.
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    html = (HERE / "template.html").read_text("utf-8")
    html = html.replace("/*DATA*/", payload).replace(
        "/*SCRIPT*/", (HERE / "app.js").read_text("utf-8").replace("</script", "<\\/script")
    )
    out = HERE / "ontology_assessment.html"
    out.write_text(html, "utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
