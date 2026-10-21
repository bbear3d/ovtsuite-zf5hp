# OVT-Suite ZF 5HP module

The ZF 5HP transmission module for [OVT-Suite](https://github.com/bbear3d/ovtsuite): the ZF 5HP19 (VW
"01V") and 5HP24/24A (VW "01L") Bosch TCUs -- the CRC-16/XMODEM checksum and
the calibration tables, which the module finds structurally in the image
itself (ZF's self-describing maps). It bundles no definition file: no WinOLS
map pack or other third-party definition is part of it.

Identification, the `.sgo` container decode and the experimental K-line
flasher are part of the base app, not of this module.

## Licence

This module is free software under the Mozilla Public License 2.0 (`LICENSE`,
and `ovtsuite/zf5hp/LICENSE.txt`, which travels in the built package).

## Building

The module is laid out exactly as it sits inside the OVT-Suite source tree.
Copy this repository's files over a checkout of the base app (same paths),
then:

    python tools/build_modules.py packages --modules zf5hp --unsigned

That writes `dist/modules/zf5hp-<version>.ovtmod`. A module you build is not
signed with the official key, so the app loads it only with **Allow unsigned
modules (development)** ticked in Tools > Modules... (or `OVT_ALLOW_UNSIGNED=1`).
The signed package ships with the OVT-Suite releases.

Run its tests from the combined tree:

    python -m pytest tests/test_zf5hp.py -q

Most of them open reference images that are not published, and are skipped
without them.

## Trademarks and legal use

ZF, Volkswagen and Audi are trademarks of their owners; this project is not
affiliated with or endorsed by them. A wrong calibration can damage a
transmission and change how the vehicle drives. See `LEGAL.md` in the base app.
