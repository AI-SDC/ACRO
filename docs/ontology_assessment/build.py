"""Build the standalone ontology assessment pages.

Embeds the packaged ontology JSON files and the page script into each template
and writes the single-file HTML pages alongside them. Run after the JSON files
or page sources change:

    python docs/ontology_assessment/build.py
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
ONTOLOGY = HERE.parent.parent / "acro"
NAMES = ("analyses", "statbarns", "risks", "checks")

# (template, script, output)
PAGES = (
    ("template.html", "app.js", "ontology_assessment.html"),
    ("wizard_template.html", "wizard_app.js", "ontology_assessment_guided.html"),
)


def main() -> None:
    """Generate the single-file HTML pages."""
    data = {n: json.loads((ONTOLOGY / f"{n}.json").read_text("utf-8")) for n in NAMES}
    # Escape "<" so definitions can never close the surrounding script tag.
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    for template, script, output in PAGES:
        html = (HERE / template).read_text("utf-8")
        js = (HERE / script).read_text("utf-8").replace("</script", "<\\/script")
        html = html.replace("/*DATA*/", payload).replace("/*SCRIPT*/", js)
        (HERE / output).write_text(html, "utf-8")
        print(f"wrote {HERE / output}")


if __name__ == "__main__":
    main()
