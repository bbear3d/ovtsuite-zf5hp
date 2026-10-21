---
title: Files and checksums
order: 10
---
# Files and checksums

## How a 5HP file is recognised

A 5HP image is recognised by the two block headers the firmware itself uses:
`BT010405…-CODE-` at offset 0x8000 (the code block) and `BT010405…` at 0x60000
(the calibration block), in a 512 KB 68k image. Size is not used as the test,
so a 5HP file cannot be mistaken for an engine ECU or another transmission.

The gearbox code in the ident block (`AG5 01V` or `AG5 01L`) selects the
family — 5HP19 or 5HP24 — and the part number (for example `3B0927156AT`) is
read from the same block and shown in the status bar.

The boot sector below 0x8000 is **not** carried by the OEM `.sgo` files and is
left blank in the opened image; only the code and calibration blocks are
present.

## OEM `.sgo` files

The VAG `.sgo` flash-delivery file holds one compressed, coded area. OVT‑Suite
decodes it transparently on open and re‑encodes it on save, so an unedited
save reproduces the original file byte‑for‑byte and an edit changes only what
it must. The coding is Bosch "BCB Type1" under the fixed key for this family;
the app validates every decode against the three checks the format itself
carries (the area's own 24‑bit sum, the same sum in the area's header, and the
section's CRC‑32 field) and refuses to show anything that does not validate.

## Checksums

A 5HP image carries six CRC‑16 words (CRC‑16/XMODEM: polynomial 0x1021,
initial value 0, no reflection), one after each block and each ident/trailer
record:

| Word at | Covers | What |
|---|---|---|
| 0x0801C | 0x08000–0x0801B | code header ident |
| 0x5FFDE | 0x08000–0x5FFDD | code block (checked by the TCU at run time) |
| 0x5FFFC | 0x5FFE0–0x5FFFB | code trailer ident |
| 0x6001C | 0x60000–0x6001B | data header ident |
| **0x7FFDE** | **0x60000–0x7FFDD** | **calibration block (checked by the TCU)** |
| 0x7FFFC | 0x7FFE0–0x7FFFB | data trailer ident |

Editing calibration changes only the 0x7FFDE word; **Save** recomputes all six
so the file always matches what a genuine tool would write. When the file came
from a `.sgo`, the area's internal sums and the section's CRC‑32 field are
refreshed too.

## Byte‑swapped reads

Some bench/BDM readers of the 16‑bit‑wide flash save the image with the two
bytes of every 16‑bit word exchanged. OVT‑Suite detects this from the block
headers, opens the image in the TCU's own byte order so maps and checksums are
correct, and — for a plain image — **saves it back byte‑swapped exactly as it
came in**. The load note says when this has happened. A file opened from a
`.sgo` is always in native order and is unaffected.
