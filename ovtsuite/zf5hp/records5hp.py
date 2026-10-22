# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""Structural table discovery for ZF 5HP calibrations.

The ZF 5HP TCU stores its maps self-describingly, in the SAME on-image
convention measured for the ZF 6HP (project memory ``zf6hp-storage-model``)
and confirmed here by disassembling the 5HP interpolation routine at image
0x10E10 (big-endian, Z row-major):

    [u16 nx][u16 ny][nx·u16 X][ny·u16 Y][nx·ny·u16 Z]

So the module finds its own tables in any 5HP image; no per-file definition
ships. A table is classed by its axes, which decides what it is far more
reliably than any assumption carried over from the 6HP:

* **map**     - both axes are real, strictly-increasing breakpoints.
* **indexed** - X is a run of consecutive label indices, Y is a real axis.
* **matrix**  - both axes are label-index runs (a label x label table).

**5HP is a 5-SPEED.** Any 6HP analogy must be adapted to that before it is used
to name anything: a selector or axis with six entries is NOT "gears 1-6" here
(the 6HP is a 6-speed; the 5HP19/24 has five). Index-run axes are therefore
left as neutral index axes, and nothing is labelled by gear. The only
physically-labelled family is the one the 5HP code itself grounds (below);
every other table keeps a plain address label until its own code is read.
"""
from __future__ import annotations

import struct
from typing import List

from ..definitions.model import AxisDef, Definition, Storage, TableDef

CAL_LO, CAL_HI = 0x60000, 0x78000
_MAXN = 40


def _s16(v: int) -> int:
    return v - 0x10000 if v >= 0x8000 else v


def _increasing(vals) -> bool:
    sv = [_s16(v) for v in vals]
    return all(sv[i] < sv[i + 1] for i in range(len(sv) - 1))


def _index_run(vals) -> bool:
    v = list(vals)
    return len(v) >= 2 and v[0] in (0, 1) and all(v[i + 1] - v[i] == 1
                                                  for i in range(len(v) - 1))


#: The one family the 5HP code grounds: the 0x10E10 lookup, indexed by a signed
#: load signal (X = $FFFF8364) and a SPEED (Y = $FFFF835A; the on-image Y axis
#: is rpm, 1000-6000), chosen by a six-STATE selector ($FFFF877F, a mode/state -
#: NOT gears; this is a 5-speed), feeding a per-state pressure/current
#: computation. A speed-ratio appears only as a tail correction factor, never as
#: the lookup index, so no slip/TCC claim is made. Which subsystem this serves
#: (shift pressure, line pressure or converter clutch) is not proven from the
#: code; the label stays descriptive and makes no functional claim.
#:
#: Identified STRUCTURALLY, not by address: the six members are 4x4 maps with a
#: signed-load X axis and a strictly-increasing rpm Y axis. Address-based ID
#: breaks across software builds -- the DATA layout is relocated between the
#: E-series (E46722/E35722, family at 0x70AFC) and the G-series (G35208, family
#: at 0x70A82), and the axes are rescaled per engine -- but this shape+axis
#: signature finds exactly the six members in every reference image.
_FAMILY_LABEL = "Control map — load × speed (6-state) 0x%05X"
_REG_MIN = 4   # a lone 4x4 signed-load x rpm map is ignored; the family clusters


def is_regulator_axes(nx: int, ny: int, xs, ys) -> bool:
    """True when a table's axes match the load x speed regulator family: 4x4,
    a signed-load X axis and a strictly-increasing rpm Y axis. ``xs``/``ys`` are
    SIGNED, decoded axis values. Shared by the structural label finder and the
    cross-binary comparison numbering (session5hp) so both agree on membership
    regardless of address or per-engine axis rescaling."""
    if (nx, ny) != (4, 4) or len(xs) != 4 or len(ys) != 4:
        return False
    return (any(x < 0 for x in xs)                         # signed load axis
            and all(ys[i] < ys[i + 1] for i in range(3))   # increasing
            and ys[0] >= 400 and ys[-1] >= 3000)           # rpm-like range


def is_rpm_torque_axes(nx: int, ny: int, xs, ys) -> bool:
    """True for the 8x8 rpm x load/torque map family (the 0x63D16 group): both
    axes strictly increasing, X an rpm-like sweep, Y a load/torque-like sweep.
    8x8 is exclusive to this family across the reference corpus. This is a
    cross-build PAIRING signature only -- the family's function is not grounded
    from code, so it carries no functional label; the signature just gives the
    group a stable identity for comparison."""
    if (nx, ny) != (8, 8) or len(xs) != 8 or len(ys) != 8:
        return False
    inc = lambda a: all(a[i] < a[i + 1] for i in range(len(a) - 1))
    return (inc(xs) and inc(ys)
            and xs[0] >= 200 and xs[-1] >= 3000     # rpm-like X
            and ys[0] >= 0 and ys[-1] >= 100)       # load/torque-like Y


def is_temp_comp_axes(nx: int, ny: int, xs, ys) -> bool:
    """The 6x5 temperature-compensation family: a 5-point temperature Y axis
    (strictly increasing, coded ~0..160) over a load/condition X. One contiguous
    run of 12 in every reference image, and 6x5 is exclusive to it. A cross-build
    PAIRING signature only -- the family's function is not grounded from code, so
    it carries no functional label."""
    if (nx, ny) != (6, 5) or len(ys) != 5:
        return False
    return (all(ys[i] < ys[i + 1] for i in range(4))
            and 0 <= ys[0] <= 40 and 90 <= ys[-1] <= 160)


def _regulator_bases(img: bytes) -> set:
    """Base addresses of the load x speed regulator family (see above), found by
    axis signature so it generalises across relocated/rescaled builds. Returned
    only when at least ``_REG_MIN`` members cluster, so a coincidental lone map
    is never labelled."""
    hits = []
    for _kind, p, nx, ny, _size in _found(img):
        X = [_s16(v) for v in struct.unpack_from(">%dH" % nx, img, p + 4)]
        Y = [_s16(v) for v in struct.unpack_from(">%dH" % ny, img, p + 4 + 2 * nx)]
        if is_regulator_axes(nx, ny, X, Y):
            hits.append(p)
    return set(hits) if len(hits) >= _REG_MIN else set()


def _found(img: bytes):
    """Yield ``(kind, addr, nx, ny, size)`` for each self-describing map.
    kind in {"map","indexed","matrix"}; curves are not emitted (their 1-D
    signature is too weak without the curve interp routine)."""
    from ..platforms.zf5hp import cal_range
    lo, hi = cal_range(img)
    p, n = lo, min(hi, len(img))
    while p + 4 <= n:
        nx, ny = struct.unpack_from(">HH", img, p)
        if 2 <= nx <= _MAXN and 2 <= ny <= _MAXN:
            size = 4 + 2 * (nx + ny + nx * ny)
            if p + size <= n:
                X = struct.unpack_from(">%dH" % nx, img, p + 4)
                Y = struct.unpack_from(">%dH" % ny, img, p + 4 + 2 * nx)
                xi, yi = _index_run(X), _index_run(Y)
                if (xi or _increasing(X)) and (yi or _increasing(Y)):
                    kind = "matrix" if (xi and yi) else "indexed" if xi else "map"
                    yield (kind, p, nx, ny, size)
                    p += size
                    continue
        p += 2


def _be16(addr: int, signed: bool) -> Storage:
    return Storage(addr=addr, bits=16, signed=signed, endian=">")


def definition(img: bytes, title: str = "ZF 5HP (structural)") -> Definition:
    """A :class:`Definition` of the self-describing maps in ``img`` (a flat,
    native big-endian 5HP image). Axes read from the image; Z row-major."""
    tables: List[TableDef] = []
    reg = _regulator_bases(img)
    for kind, p, nx, ny, _size in _found(img):
        x = AxisDef(nx, values=_be16(p + 4, signed=True))
        y = AxisDef(ny, values=_be16(p + 4 + 2 * nx, signed=True))
        z = _be16(p + 4 + 2 * (nx + ny), signed=False)
        if kind == "matrix":
            name = "ZF 5HP indexed matrix 0x%05X (%dx%d)" % (p, nx, ny)
        elif kind == "indexed":
            name = "ZF 5HP indexed table 0x%05X (%dx%d)" % (p, nx, ny)
        elif p in reg:
            name = _FAMILY_LABEL % p
        else:
            name = "ZF 5HP map 0x%05X (%dx%d)" % (p, nx, ny)
        tables.append(TableDef(name=name, kind="map", z=z, rows=ny, cols=nx,
                               x=x, y=y, order="row"))
    return Definition(type="zf5hp", title=title, tables=tables, base=0)
