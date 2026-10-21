---
title: ZF 5HP
---
# ZF 5HP

The ZF 5HP module works on files from the ZF 5HP19 (VW gearbox code "01V") and
5HP24 / 5HP24A ("01L") five-speed transmission control units — the Bosch-built
TCUs used across late‑1990s and 2000s VW-group cars (TCU part numbers
`3B0927156…` for the 5HP19, `4B0927156…` for the RS6 5HP24, and related). It
recognises the image, reads its calibration maps where a definition exists,
corrects the checksums when you save, and reads the OEM `.sgo` flash files
directly.

> **Free and open source.** Unlike the other transmission modules, the ZF 5HP
> module is published under the MPL‑2.0 — its source is public and its licence
> text ships with the module (`LICENSE.txt`).

> **Early version (0.1).** Coverage is growing. The 5HP24 (RS6) calibration
> has a full map definition; the 5HP19 opens with its checksum and the hex
> editor while its named map set is built. Flashing is **experimental and
> disabled** in this version (see [Flashing](flashing.md)).

## What can be opened

| File | Notes |
|---|---|
| OEM `.sgo` | The VAG flash-delivery file; decoded in the app (see [Files and checksums](files.md)) |
| Full 512 KB image | As read from the TCU or exported by another tool, in either byte order (see below) |

## Pages in this section

| Page | What it covers |
|---|---|
| [Files and checksums](files.md) | Identification, the `.sgo` container, the CRC‑16 checksums, and byte‑swapped reads |
| [Flashing](flashing.md) | Why TCU flashing is experimental and currently disabled |

## See also

- [ZF 6HP](../zf6hp/index.md) and [ZF 8HP](../zf8hp/index.md) — the other
  transmission modules; the display modes work the same way.
- [Editing tables](../../editing.md) and [The main window](../../interface.md).
