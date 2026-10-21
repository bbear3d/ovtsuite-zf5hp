# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""ZF 5HP19 / 5HP24 image checksums.

A 5HP image carries six **CRC-16/XMODEM** words (poly 0x1021, init 0, no
reflection, big-endian), one after each of its two blocks and its four
ident/trailer records. Each word follows the range it protects, so the
running CRC returns to 0 and an ident word equals the CRC from its block's
start -- established against the 5HP19 (01V) and RS6 5HP24 (01L) reference
images, where all six reproduce exactly. See project doc
``zf5hp19_feasibility.md`` §3.

    slot      covers (inclusive)      what
    0x0801C   0x08000-0x0801B         code header ident
    0x5FFDE   0x08000-0x5FFDD         CODE block  (TCU runtime check)
    0x5FFFC   0x5FFE0-0x5FFFB         code trailer ident
    0x6001C   0x60000-0x6001B         data header ident
    0x7FFDE   0x60000-0x7FFDD         DATA/calibration block (runtime check)
    0x7FFFC   0x7FFE0-0x7FFFB         data trailer ident

A calibration edit changes only the DATA block, so in practice only 0x7FFDE
moves; :func:`correct` rewrites all six so the result always matches a genuine
file. The ranges are structural constants of the format, not guesses, and the
block headers (``BT010405`` at 0x8000 and 0x60000) are what :func:`is_supported`
keys on.
"""
from dataclasses import dataclass, field
from typing import List, Tuple

from ..modules.api import ChecksumError

_MARK = b"BT"       # block-header prefix; version chars vary (010405/010504)
_CODE_TAG = b"-CODE-"
_CODE_HDR = 0x8000
_DATA_HDR = 0x60000
_IMAGE = 0x80000

#: (slot, start, end-inclusive). Order matters for :func:`correct`: the small
#: ident words are written before the two big block CRCs that cover them.
FIELDS: Tuple[Tuple[int, int, int], ...] = (
    (0x0801C, 0x08000, 0x0801B),
    (0x6001C, 0x60000, 0x6001B),
    (0x5FFFC, 0x5FFE0, 0x5FFFB),
    (0x7FFFC, 0x7FFE0, 0x7FFFB),
    (0x5FFDE, 0x08000, 0x5FFDD),
    (0x7FFDE, 0x60000, 0x7FFDD),
)

_TABLE = []
for _i in range(256):
    _c = _i << 8
    for _ in range(8):
        _c = ((_c << 1) ^ 0x1021) & 0xFFFF if _c & 0x8000 else (_c << 1) & 0xFFFF
    _TABLE.append(_c)


def crc16(data: bytes) -> int:
    """CRC-16/XMODEM of ``data``."""
    c = 0
    for b in data:
        c = ((c << 8) & 0xFFFF) ^ _TABLE[((c >> 8) ^ b) & 0xFF]
    return c


def _check(data) -> None:
    if len(data) < _IMAGE:
        raise ChecksumError("image is %d bytes, a 5HP image is %d" % (len(data), _IMAGE))
    if (data[_CODE_HDR:_CODE_HDR + 2] != _MARK
            or data[_CODE_HDR + 0x0E:_CODE_HDR + 0x14] != _CODE_TAG
            or data[_DATA_HDR:_DATA_HDR + 2] != _MARK):
        raise ChecksumError("no ZF 5HP BT block headers at 0x8000/0x60000")


@dataclass
class FieldReport:
    slot: int
    start: int
    end: int
    stored: int
    computed: int

    @property
    def ok(self) -> bool:
        return self.stored == self.computed

    def describe(self) -> str:
        return ("CRC-16 @0x%05X over 0x%05X-0x%05X: stored 0x%04X, computed 0x%04X (%s)"
                % (self.slot, self.start, self.end, self.stored, self.computed,
                   "valid" if self.ok else "correction needed"))


@dataclass
class Report:
    fields: List[FieldReport] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(f.ok for f in self.fields)

    def describe(self) -> str:
        head = "ZF 5HP checksums: %s" % ("all valid" if self.ok else "correction needed")
        return "\n".join([head] + ["  " + f.describe() for f in self.fields])


def is_supported(data) -> bool:
    try:
        _check(data)
        return True
    except ChecksumError:
        return False


def verify(data, **_kw) -> Report:
    _check(data)
    data = bytes(data)
    rep = Report()
    for slot, start, end in sorted(FIELDS):
        stored = (data[slot] << 8) | data[slot + 1]
        rep.fields.append(FieldReport(slot, start, end, stored, crc16(data[start:end + 1])))
    return rep


def correct(data, **_kw) -> bytes:
    """A copy of ``data`` with all six CRC-16 words rewritten (the small ident
    words first, so the two block CRCs that span them are computed over the
    corrected bytes)."""
    _check(data)
    buf = bytearray(data)
    for slot, start, end in FIELDS:
        c = crc16(bytes(buf[start:end + 1]))
        buf[slot] = (c >> 8) & 0xFF
        buf[slot + 1] = c & 0xFF
    return bytes(buf)


def exempt_ranges(data, **_kw) -> List[Tuple[int, int]]:
    """The six stored CRC words -- bytes that change whenever their block
    does, so a byte-level diff shouldn't flag them."""
    if not is_supported(data):
        return []
    return [(slot, slot + 2) for slot, _s, _e in FIELDS]
