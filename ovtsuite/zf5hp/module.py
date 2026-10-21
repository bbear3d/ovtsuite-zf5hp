# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""The ZF 5HP module's declaration (see :mod:`ovtsuite.modules.api`).

Unlike the other transmission modules, the ZF 5HP module is published **free
and open source under the MPL-2.0** -- every file carries the MPL header and
the package ships its own ``LICENSE.txt`` rather than the module EULA.

Covers the ZF 5HP19 (VW "01V") and 5HP24/24A (VW "01L") Bosch TCUs:
checksum (CRC-16/XMODEM, :mod:`.checksum5hp`), tables found structurally
(:mod:`.session5hp`), and -- experimentally, gated off until bench-proven --
K-line flashing (:mod:`ovtsuite.flash.zf5hp`). The container decode (the
``GEHEIM`` BCB Type1 ``.sgo``) lives in the base :mod:`ovtsuite.sgo`.
"""
from ..modules import api as _api

#: The module's own version (independent of the app's); bump on any change.
MODULE = _api.ModuleSpec(
    id="zf5hp", name="ZF 5HP", version="0.1.0",
    platforms=("zf5hp",),
    capabilities=(_api.CHECKSUM, _api.DEFINITIONS),
    build=".session5hp:build",
    checksum=".module:checksum",
    data=(),                       # no bundled definition: tables are found structurally
    license={"required": False, "terms": "MPL-2.0"},
)


def checksum(session=None):
    from . import checksum5hp
    return _api.FunctionsProvider(checksum5hp, "ZF 5HP")
