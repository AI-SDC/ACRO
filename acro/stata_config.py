"""
Stata config file.

Holds global variable for acro object accessible from acro files and stata
mutable hence use of lower case naming.

Jim Smith 2023.
"""

from typing import Any

import acro

stata_acro: Any = acro.ACRO()
