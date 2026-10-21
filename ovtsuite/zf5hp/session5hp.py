# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Populate a :class:`~ovtsuite.session.TunerSession` for a ZF 5HP image.

The definition is built STRUCTURALLY from the image itself
(:mod:`ovtsuite.zf5hp.records5hp`): the ZF 5HP maps are self-describing, so the
module finds them in any image and ships no per-file definition. This applies
to every variant -- the 5HP19 (01V) and the 5HP24 (01L) alike; no WinOLS pack
is used in the product. The found axes are flipped to the loaded image's byte
order (the base app standardises on native 68k big-endian for 5HP -- see
``zf5hp19_feasibility.md``) so :func:`ovtsuite.xdf_session.entities` reads them
rather than dropping them as wrong-order.
"""
from typing import List, Optional

from ..model import Entity
from ..progress import Reporter


def _to_image_order(defn, endian: str) -> None:
    """Force every multi-byte storage to the loaded image's byte order, so a
    table read in the other order is not dropped."""
    for t in defn.tables:
        stores = [t.z]
        if t.x is not None:
            stores.append(t.x.values)
        if t.y is not None:
            stores.append(t.y.values)
        for st in stores:
            if st is not None and st.bits > 8:
                st.endian = endian


def _number_families(entities) -> int:
    """Give the load x speed regulator family a layout-independent identity so a
    cross-binary comparison pairs it even when the DATA region is relocated
    (G-series software) or the axes are rescaled per engine.

    Same approach as the ZF 6HP shift/TCC numbering (``anchors6hp``): position
    within the family run is the identity, and the member count is part of the
    key so two images that disagree on the count fail to pair rather than
    mis-pair. The run is read in address order, which is the firmware's state
    order -- the 0x86AE selector ``pea``'s the members in state order -- so the
    i-th member is the same per-state control map across builds and engines.
    Without this, these structurally-found tables carried only a byte-address
    identity (``TunerSession._struct_key``) and paired with nothing across a
    relocated layout, so the control maps -- the ones you open a comparison to
    tune -- were invisible to the overlay."""
    from . import records5hp
    _MIN = 4   # families cluster; a lone match is not numbered

    def _number(pred, tag):
        grp = [e for e in entities
               if pred(e.cols, e.rows, e.x_values(), e.y_values())]
        if len(grp) < _MIN:
            return 0
        grp.sort(key=lambda e: e.addr)   # address order == firmware run order
        for i, e in enumerate(grp):
            e.scan_key = (tag, len(grp), i)
        return len(grp)

    # the code-grounded load x speed regulator, and the 8x8 rpm x torque group
    # (pairing identity only -- its function is not grounded from code)
    n = _number(records5hp.is_regulator_axes, "zf5hp:reg")
    n += _number(records5hp.is_rpm_torque_axes, "zf5hp:rpmtq")
    n += _number(records5hp.is_temp_comp_axes, "zf5hp:tempc")
    return n


def build(session, family: Optional[str] = None, progress=None) -> None:
    rep = Reporter.of(progress, "zf5hp")
    data = bytes(session.binfile.data)

    session.platform = "zf5hp"
    session.datasets = []             # EDC15-only fields the GUI reads defensively
    session.match15 = None
    session.message_table = None
    session.family_choice = None
    session.region = (0, len(data))
    session.entities: List[Entity] = []
    session.by_key = {}

    rep.step("Reading the ZF 5HP image")
    from ..platforms import zf5hp as _id
    facts = _id.describe(data)
    fam = facts.get("family", "5HP")
    part = facts.get("part", "")
    session.family = " ".join(x for x in (fam, part) if x) or "ZF 5HP"

    rep.step("Finding the ZF 5HP tables")
    from . import records5hp
    defn = records5hp.definition(data)
    _to_image_order(defn, getattr(session.binfile, "endian", ">") or ">")

    rep.step("Building the parameter tree")
    from .. import xdf_session
    session.entities = xdf_session.entities(defn, session.binfile)
    _number_families(session.entities)
    session.family_note = (
        "ZF 5HP image (%s): %d self-describing tables found structurally. "
        "Axes are read from the image; the load × speed control family is "
        "labelled from the firmware's own lookup routine. Other tables carry "
        "their address until their own code names them. (5HP is a five-speed -- "
        "no 6HP gear assumptions are applied; gear/shift structure appears as "
        "sibling-map families, never as an axis width.)"
        % (session.family, len(session.entities)))
