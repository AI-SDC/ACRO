#!/usr/bin/env python3
"""
Reformat the first version section of CHANGELOG.md to match project style.

- Header: ## Version X.Y.Z (Mon DD, YYYY)  (add date, no colon after Version)
- Bullets: *   <text>: description ([#N](url))  (PR title + PR link; titles have no link).
Only the first version block (the one Changelog CI just added) is modified.
"""

import re
import sys
from datetime import datetime
from pathlib import Path


def main() -> None:
    """Reformat the first version block in CHANGELOG.md to project style and write back."""
    path = Path(__file__).resolve().parent.parent.parent / "CHANGELOG.md"
    if not path.exists():
        print("CHANGELOG.md not found", file=sys.stderr)
        sys.exit(1)

    text = path.read_text()
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    in_first_block = False
    date_str = datetime.utcnow().strftime("%b %d, %Y")  # e.g. Feb 26, 2026

    # Match Changelog CI header: "## Version: 0.4.13" or "## Version 0.4.13"
    version_header_re = re.compile(
        r"^(\s*##\s+Version):?\s+([0-9]+\.[0-9]+\.[0-9]+)\s*\n$"
    )
    # Match Changelog CI bullet: "* #273: feat: description" -> *   feat: description ([#273](url))
    bullet_re = re.compile(r"^(\s*\*)\s+#(\d+):\s+(.*)$")
    pr_base_url = "https://github.com/AI-SDC/ACRO/pull"
    # Next version section (end of first block)
    next_version_re = re.compile(r"^\s*##\s+Version\s+")

    for line in lines:
        if next_version_re.match(line) and in_first_block:
            in_first_block = False
        m = version_header_re.match(line)
        if m and not in_first_block:
            # First version header: conform to ## Version 0.4.12 (Feb 02, 2026)
            out.append(f"{m.group(1)} {m.group(2)} ({date_str})\n")
            in_first_block = True
            continue
        if in_first_block and (b := bullet_re.match(line)):
            # Conform: *   feat: description ([#N](url))
            rest = b.group(3).rstrip()
            pr_num = b.group(2)
            out.append(f"{b.group(1)}   {rest} ([#{pr_num}]({pr_base_url}/{pr_num}))\n")
            continue
        out.append(line)

    path.write_text("".join(out))
    print("Reformatted first version section of CHANGELOG.md to match project style.")


if __name__ == "__main__":
    main()
