---
title: Flashing
order: 20
---
# Flashing (experimental, disabled)

TCU flashing for the ZF 5HP is **experimental and not enabled** in this
version. OVT‑Suite can identify a 5HP, read and edit its calibration from a
file, and correct its checksums — but it will not write to the TCU yet.

## Why it is held back

On these TCUs the flash‑programming routines — the security unlock, the erase
and the download — do not live in the part of the flash that the `.sgo` files
or a normal read contain. They are in the microcontroller's internal boot ROM,
which is reached only by putting the TCU into a programming mode that has not
yet been captured. The security unlock uses VAG's SA2 challenge/response: the
`.sgo` carries the tester's half of it (the SA2 program), and OVT‑Suite can run
that program on a seed, but the exact erase and download framing — and the
confirmation that the computed key is accepted — can only be established safely
by watching a working flash tool on a bench TCU, or by reading the boot ROM.

Until that is done, flashing an unproven sequence could leave a TCU
unrecoverable, so the write path refuses to run rather than risk it.

## What works today instead

- **Identify** a 5HP file and see its part number and gearbox code.
- **Open and edit** the calibration, with the checksum corrected on save.
- **Read** the matching OEM `.sgo` from the file library when you need a known‑
  good base to edit.

## What would enable it

A single capture of a known‑good flash tool writing a 5HP over K‑line (to
record the seed→key exchange and the erase/download framing), or a boot‑ROM
dump of the microcontroller. With either in hand, the write path can be
validated on the bench and switched on.
