# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""ZF 5HP TCUs (5HP19 / VW "01V", 5HP24/24A / VW "01L") -- the ZF 5HP module.

Free and open source under the MPL-2.0 (its own ``LICENSE.txt``), unlike the
other transmission modules. Today: the checksum (CRC-16/XMODEM,
:mod:`.checksum5hp`) and the tables, found structurally (:mod:`.session5hp`).
Identification is base-app knowledge (:mod:`ovtsuite.platforms.zf5hp`) and the
``GEHEIM`` BCB Type1 ``.sgo`` decode is in :mod:`ovtsuite.sgo`. Experimental
K-line flashing is the flasher's (:mod:`ovtsuite.flash.zf5hp`), gated off
until bench-proven.
"""
