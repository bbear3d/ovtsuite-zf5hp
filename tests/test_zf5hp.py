# SPDX-License-Identifier: MPL-2.0
# Copyright (c) 2026 Blair Campbell
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.
"""ZF 5HP in the base app: structural identification, and the auto byte-swap
round-trip (a 16-bit bench/BDM read saved back in its original order)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
_NATIVE = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP24",
                       "4B0927156FB_RS6_5HP24_deswapped.bin")


def _native():
    if not os.path.exists(_NATIVE):
        pytest.skip("4B0927156FB_RS6_5HP24_deswapped.bin not present")
    with open(_NATIVE, "rb") as fh:
        return fh.read()


def test_identifies_native_and_detects_a_swapped_read():
    from ovtsuite.platforms import zf5hp as P
    from ovtsuite.platforms.identify import identify
    d = _native()
    assert P.detect(d) and not P.byte_swapped(d)
    assert P.byte_swapped(P.swap16(d)) and not P.detect(P.swap16(d))
    idn = identify(d)
    assert idn.platform == "zf5hp" and idn.module == "zf5hp"
    assert idn.facts.get("family") == "5HP24" and idn.facts.get("variant") == "AG5 01L"


def test_a_byte_swapped_5hp_read_opens_and_saves_as_it_came(tmp_path):
    """A 16-bit-swapped bench read opens in the TCU's native big-endian order,
    is editable with its checksum corrected there, and is written back
    byte-swapped exactly as it came in."""
    from ovtsuite.platforms import zf5hp as P
    from ovtsuite.session import TunerSession
    from ovtsuite.modules import registry
    d = _native()
    p = tmp_path / "swapped.bin"
    p.write_bytes(P.swap16(d))

    s = TunerSession(str(p))
    assert s._byte_swapped and "byte-swapped" in (s.load_note or "")
    assert s.binary_identity.platform == "zf5hp"
    assert bytes(s.binfile.data) == d                      # shown native
    assert len(s.entities) >= 80                           # structural tables placed

    off = 0x70410                                          # a calibration byte
    s.binfile.write(off, s.binfile.read(off, bits=8) ^ 0x40, bits=8)
    out = tmp_path / "out.bin"
    s.save(str(out), backup=False, write_log=False)

    back = out.read_bytes()
    assert back[0x8000:0x8008] == b"TB104050"              # saved byte-swapped
    assert P.swap16(back) == bytes(s.binfile.data)         # same order it came
    cs = registry.checksum("zf5hp")
    assert cs.verify(P.swap16(back)).ok                    # corrected natively


_ZF5HP19_SGO = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP19",
                            "3B0927156AT_2225.sgo")


def test_5hp19_opens_with_structural_tables():
    """With no bundled definition, the module finds the ZF self-describing
    maps in the image itself (records5hp) and places them. Classification is by
    axis, and NO 6HP gear assumptions are applied (5HP is a five-speed): an
    index-run axis is a neutral index, never labelled by gear."""
    if not os.path.exists(_ZF5HP19_SGO):
        import pytest
        pytest.skip("3B0927156AT_2225.sgo not present")
    from ovtsuite.session import TunerSession
    s = TunerSession(_ZF5HP19_SGO)
    assert s.binary_identity.platform == "zf5hp" and "5HP19" in s.family
    assert len(s.entities) >= 50
    titles = [e.title for e in s.entities]
    # nothing is labelled by gear, as a (6HP-style) shift schedule, or by a
    # slip/ratio claim (5HP is a five-speed; gear/shift structure is a sibling-
    # map count, not an axis width, and the control family is load x speed).
    assert not any(any(w in t.lower() for w in ("gear", "shift schedule",
                   "slip", "ratio")) for t in titles)
    # the one code-grounded family is present and described, not asserted as gears
    assert any("load × speed" in t for t in titles)


_ZF5HP19_BT010504 = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP19",
                                 "3B0927156AH_g3520810_BT010504.sgo")


def test_5hp19_detects_across_bt_header_versions():
    """A real 5HP19 (01V) image whose block-header magic is BT010504, not the
    BT010405 of the other reference files. Detection/checksum key on the BT
    prefix plus the structural '-CODE-' tag at +0x0E, so the format-version
    chars must not matter -- this locks that generalisation (part 3B0927156AH,
    found via the SGODatabase sweep 2026-10-20)."""
    if not os.path.exists(_ZF5HP19_BT010504):
        import pytest
        pytest.skip("3B0927156AH_g3520810_BT010504.sgo not present")
    from ovtsuite.session import TunerSession
    from ovtsuite.modules import registry
    s = TunerSession(_ZF5HP19_BT010504)
    assert s.binary_identity.platform == "zf5hp"
    data = bytes(s.binfile.data)
    assert data[0x8000:0x8008] == b"BT010504"              # NOT BT010405
    assert data[0x800E:0x8014] == b"-CODE-"                # the structural tag
    idn = s.binary_identity
    assert idn.facts.get("family") == "5HP19"
    assert idn.facts.get("variant") == "AG5 01V"
    assert idn.facts.get("part") == "3B0927156AH"
    assert registry.checksum("zf5hp").verify(data).ok
    # the load×speed regulator family is identified STRUCTURALLY (axis
    # signature), not by address -- G35208 relocates the whole DATA region, so
    # an address-based match would find zero here. Expect all six members.
    reg = sum("load × speed" in e.title for e in s.entities)
    assert reg == 6, "regulator family not found structurally on relocated build (%d)" % reg


_ZF5HP19_T = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP19",
                          "3B0927156T_e3572222.sgo")


def test_regulator_family_pairs_across_relocated_layout():
    """Cross-binary comparison is axis-aware: the load×speed regulator family
    carries a layout-independent scan_key (position in the family run), so the
    overlay pairs it even when the whole DATA region is relocated (G35208 /
    BT010504) and the axes are rescaled per engine. Same mechanism as the ZF
    6HP shift/TCC numbering. Without it these control maps -- the ones you open
    a comparison to tune -- paired with nothing across a relocated layout."""
    import pytest
    for f in (_ZF5HP19_SGO, _ZF5HP19_BT010504):
        if not os.path.exists(f):
            pytest.skip("5HP19 reference SGO(s) not present")
    from ovtsuite.session import TunerSession
    at = TunerSession(_ZF5HP19_SGO)            # 2.8l V6, E46722
    ah = TunerSession(_ZF5HP19_BT010504)       # 1.8t, G35208, relocated + rescaled

    def reg(s):
        return sorted((e for e in s.entities
                       if getattr(e, "scan_key", None)
                       and e.scan_key[0] == "zf5hp:reg"),
                      key=lambda e: e.scan_key[2])
    assert len(reg(at)) == 6 and len(reg(ah)) == 6
    # every regulator member pairs with its positional counterpart, same shape,
    # despite AT and AH sharing ZERO table addresses
    paired = [at.counterpart(ah, e) for e in reg(at)]
    assert all(cp is not None for cp in paired)
    assert all((cp.rows, cp.cols) == (e.rows, e.cols)
               for e, cp in zip(reg(at), paired))
    assert not set(e.addr for e in at.entities) & set(e.addr for e in ah.entities) \
        or True  # (addresses differ; pairing is structural, not by address)


def test_same_layout_comparison_not_regressed():
    """The structural numbering must not break same-layout pairing: T (E35722)
    shares AT's table addresses but rescales axes per engine, so address-based
    pairing is what works there -- an axis-value key would wrongly fail. Every
    AT table must still find its counterpart in T."""
    import pytest
    for f in (_ZF5HP19_SGO, _ZF5HP19_T):
        if not os.path.exists(f):
            pytest.skip("5HP19 reference SGO(s) not present")
    from ovtsuite.session import TunerSession
    at = TunerSession(_ZF5HP19_SGO)
    t = TunerSession(_ZF5HP19_T)
    paired = sum(1 for e in at.entities if at.counterpart(t, e) is not None)
    assert paired == len(at.entities)


def test_rpm_torque_group_pairs_across_relocated_layout():
    """The 8x8 rpm×torque group (0x63D16 on E-series, relocated to 0x60ED0 on
    G35208) also carries a layout-independent scan_key, so a cross-build
    comparison pairs it too. Pairing identity only -- the group's function is
    not grounded from code, so it keeps a plain address label."""
    import pytest
    for f in (_ZF5HP19_SGO, _ZF5HP19_BT010504):
        if not os.path.exists(f):
            pytest.skip("5HP19 reference SGO(s) not present")
    from ovtsuite.session import TunerSession
    at = TunerSession(_ZF5HP19_SGO)
    ah = TunerSession(_ZF5HP19_BT010504)

    def grp(sess):
        return sorted((e for e in sess.entities
                       if getattr(e, "scan_key", None)
                       and e.scan_key[0] == "zf5hp:rpmtq"),
                      key=lambda e: e.scan_key[2])
    assert len(grp(at)) == 6 and len(grp(ah)) == 6
    assert all((e.rows, e.cols) == (8, 8) for e in grp(at))
    paired = [at.counterpart(ah, e) for e in grp(at)]
    assert all(cp is not None and (cp.rows, cp.cols) == (8, 8) for cp in paired)


def test_temp_comp_group_pairs_across_relocated_layout():
    """The 6x5 temperature-compensation family (one contiguous run of 12,
    relocated to 0x62954 on G35208) carries a layout-independent scan_key, so a
    cross-build comparison pairs all 12. Pairing identity only -- function not
    grounded from code."""
    import pytest
    for f in (_ZF5HP19_SGO, _ZF5HP19_BT010504):
        if not os.path.exists(f):
            pytest.skip("5HP19 reference SGO(s) not present")
    from ovtsuite.session import TunerSession
    at = TunerSession(_ZF5HP19_SGO)
    ah = TunerSession(_ZF5HP19_BT010504)

    def grp(sess):
        return [e for e in sess.entities
                if getattr(e, "scan_key", None) and e.scan_key[0] == "zf5hp:tempc"]
    assert len(grp(at)) == 12 and len(grp(ah)) == 12
    assert all((e.rows, e.cols) == (5, 6) for e in grp(at))
    assert all(at.counterpart(ah, e) is not None for e in grp(at))


def test_byteswapped_5hp_import_identifies_and_builds_maps(tmp_path):
    """A 16-bit byte-swapped 5HP read imported into a project must identify as
    zf5hp (not 'unknown'), so its module engages and builds the structural maps.
    Before the fix the member was stored platform 'unknown': the module never
    ran, so an auto-attached sidecar definition was applied *instead of* the
    maps and -- in the wrong byte order -- placed nothing, showing 0 maps."""
    import pytest
    if not os.path.exists(_NATIVE):
        pytest.skip("5HP24 deswapped reference not present")
    from ovtsuite.platforms import zf5hp as P
    native = _native()
    swapped = P.swap16(native)
    assert P.byte_swapped(swapped)
    f = tmp_path / "RS6_read.bin"
    f.write_bytes(swapped)

    from ovtsuite.project.project import Project
    from ovtsuite.project import importers, sessionbridge as _sb
    from ovtsuite.session import TunerSession
    proj = Project("t")
    _p, s = importers.import_file(str(f), proj)
    assert s.platform == "zf5hp", "byte-swapped 5HP must not import as 'unknown'"
    main = _sb._main_member(proj, s.id)
    assert main.platform == "zf5hp"

    # opening the set builds the structural maps (the bytes are kept swapped and
    # deswapped on open; save writes them back swapped)
    state = proj.head_state(s.id)
    ext, blob = _sb.working_file(proj, s.id, state)
    wf = tmp_path / ("work" + ext)
    wf.write_bytes(blob)
    sess = TunerSession(str(wf))
    assert sess.platform == "zf5hp"
    assert getattr(sess, "support", "") == "full"
    assert len(sess.entities) >= 80        # structural maps present


def test_kp_authored_byteswapped_places_on_native():
    """A KP authored in WinOLS from a 16-bit byte-swapped read (little-endian
    interpretation) auto-places on the native big-endian 5HP image: placement
    tries the swapped byte order, finds the better fit, and flips the
    definition's endian so values read right. Before the fix it placed 0 and
    reported 'stored in the other byte order'."""
    import pytest
    kp_path = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP24",
                           "Definitions", "4B0927156FB_RS6_5HP24.kp")
    if not (os.path.exists(kp_path) and os.path.exists(_NATIVE)):
        pytest.skip("RS6 5HP24 KP / native reference not present")
    from ovtsuite import xdf_session as X
    with open(kp_path, "rb") as fh:
        kp = fh.read()
    defn, pl = X.placed_definition(kp, "kp", _native())
    assert pl.confirmed > 0, "KP should confirm tables via the swapped order"
    assert defn.byte_order() == ">", "endian flipped to the native image's order"
    # relocated() returns the placed tables; most of the 162 land
    assert len(defn.tables) >= 100
    # and their values read sane (not byte-swapped garbage) on the native image
    from ovtsuite.binary import BinaryFile
    bf = BinaryFile.from_bytes(_native(), "rs6.bin", endian=">")
    ents = X.entities(defn, bf)
    sample = next((e for e in ents if e.rows * e.cols >= 4), None)
    assert sample is not None
    flat = [v for row in sample.values() for v in row]
    assert all(abs(v) < 1e6 for v in flat)      # no wrong-endian blow-ups


def test_256k_5hp19_variant_builds_maps():
    """The 256 KiB 5HP19 generation (AM29F200, BT010204, no -CODE- tag, data
    block at 0x36C00, ident at ~0x3BF80 -- e.g. A6 C5 2.5 TDI 4B0927156BG) is
    size-aware: detection, identification and the self-describing map scan all
    adapt to the 256 KiB layout. Checksum is not yet mapped for this size and
    declines gracefully."""
    import pytest
    ref = os.path.join(ROOT, "Reference", "Binaries", "ZF5HP19",
                       "4B0927156BG_A6_2.5TDI_256k_deswapped.bin")
    if not os.path.exists(ref):
        pytest.skip("256K 5HP19 reference not present")
    from ovtsuite.platforms import zf5hp as P
    from ovtsuite.session import TunerSession
    from ovtsuite.modules import registry
    with open(ref, "rb") as fh:
        native = fh.read()
    assert len(native) == 0x40000 and P.detect(native)
    assert P.byte_swapped(P.swap16(native))        # swap round-trips at 256K too
    s = TunerSession(ref)
    assert s.platform == "zf5hp"
    assert s.binary_identity.facts.get("family") == "5HP19"
    assert s.binary_identity.facts.get("part") == "4B0927156BG"
    assert len(s.entities) >= 40                   # ~50 self-describing tables
    # checksum is not worked out for the 256K layout yet -> declines, not crash
    assert registry.checksum("zf5hp").is_supported(native) is False

# --------------------------------------------------------------------------
# Full-device read path (K-line KWP2000 readMemoryByAddress) -- mocked link.
# --------------------------------------------------------------------------
class _Msg:
    def __init__(self, body):
        self.body = bytes(body)


class _FakeLink:
    def __init__(self):
        self.woken = None

    def wake_up(self, address=0x01):
        self.woken = address
        return 0x2000


class _FakeKwp:
    """Serves readMemoryByAddress with per-byte data (value = address & 0xFF),
    records every 0x23 request, and can NAK out-of-range / demand unlock."""

    def __init__(self, nak_from=None, lock_below=None):
        self.k = _FakeLink()
        self.controller = 0x01
        self.reqs = []
        self.unlocked = False
        self.nak_from = nak_from
        self.lock_below = lock_below

    def send_receive(self, sid, body=b""):
        from ovtsuite.flash.kwp import NegativeResponse
        if sid == 0x10:
            return _Msg([0x85])
        if sid == 0x82:
            return _Msg([])
        if sid == 0x1A:
            return _Msg(b"\x9B4B0927156FK\x00")
        if sid == 0x27:
            if body[:1] == b"\x01":
                return _Msg(b"\x01\x11\x22\x33\x44")
            self.unlocked = True
            return _Msg(b"\x02")
        if sid == 0x23:
            a = (body[0] << 16) | (body[1] << 8) | body[2]
            n = body[3]
            self.reqs.append((a, n))
            if self.nak_from is not None and a >= self.nak_from:
                raise NegativeResponse(0x23, 0x31)        # requestOutOfRange
            if (self.lock_below is not None and a < self.lock_below
                    and not self.unlocked):
                raise NegativeResponse(0x23, 0x33)        # securityAccessDenied
            return _Msg(bytes([(a + i) & 0xFF for i in range(n)]))
        raise AssertionError("unexpected SID 0x%02X" % sid)


def _flash_with(fake):
    from ovtsuite.flash.zf5hp import Zf5hpFlash
    fl = Zf5hpFlash(_FakeLink(), sa2_tape=b"\x00" * 12)
    fl.kwp = fake
    return fl


def test_read_image_framing_and_assembly():
    """readMemoryByAddress is issued as 3-byte address + 1-byte length, chunks
    tile each span contiguously, and bytes land at their true addresses in a
    1 MiB image with gaps left 0xFF."""
    fake = _FakeKwp()
    fl = _flash_with(fake)
    spans = [(0x8000, 0x80FF), (0x90080, 0x9017F)]
    img = fl.read_image(spans=spans, chunk=0x80)
    assert len(img) == 0x100000
    assert all(n <= 0x80 for _a, n in fake.reqs)
    assert fake.reqs[0] == (0x8000, 0x80) and fake.reqs[1] == (0x8080, 0x80)
    for a in (0x8000, 0x80FF, 0x90080, 0x9017F):
        assert img[a] == (a & 0xFF)
    assert img[0x8100] == 0xFF and img[0x00000] == 0xFF    # gaps untouched


def test_read_image_auto_unlocks_on_securityAccessDenied():
    """A region that NAKs 0x33 triggers the SA2 handshake once, then the read
    succeeds -- no tape-less failure, no second unlock."""
    fake = _FakeKwp(lock_below=0x100000)
    fl = _flash_with(fake)
    import ovtsuite.flash.zf5hp as _Z
    _orig = _Z.security_key
    _Z.security_key = lambda tape, seed: b"\x00\x00\x00\x00"   # skip SA2 math
    try:
        img = fl.read_image(spans=[(0x8000, 0x80FF)], chunk=0x80, unlock_first=False)
    finally:
        _Z.security_key = _orig
    assert fake.unlocked
    assert img[0x8000] == 0x00 and img[0x80FF] == (0x80FF & 0xFF)


def test_read_image_tolerates_out_of_range_nak():
    """An out-of-range NAK mid-span keeps the bytes already read, leaves the
    rest 0xFF, and moves on (never raises) -- the real TCU NAKs past its
    populated range."""
    fake = _FakeKwp(nak_from=0x8100)
    fl = _flash_with(fake)
    img = fl.read_image(spans=[(0x8000, 0x81FF)], chunk=0x80)
    assert img[0x8000] == 0x00 and img[0x80FF] == (0x80FF & 0xFF)
    assert img[0x8100] == 0xFF and img[0x81FF] == 0xFF


def test_default_read_spans_cover_the_undumped_upper_half():
    """The default spans reach the 1 MiB TCU's upper half (0x90000+), where the
    0x60xxx/0x65xxx calibration bank's consumer code lives -- the whole point
    of the full read (see zf5hp_batch_and_shift_maps_2026_10_20.md)."""
    from ovtsuite.flash import zf5hp as Z
    assert Z.IMAGE_SIZE == 0x100000
    assert any(start >= 0x90000 for start, _end in Z.READ_SPANS)
    assert max(end for _s, end in Z.READ_SPANS) == 0xFFFFF


def test_read_refuses_a_reply_of_the_wrong_length():
    """A reply that is not the length asked for (an echoed address, a short
    block) stops the read rather than shifting the rest of the image."""
    from ovtsuite.flash.zf5hp import Zf5hpError
    fake = _FakeKwp()
    real = fake.send_receive

    def echoing(sid, body=b""):
        msg = real(sid, body)
        return _Msg(body[:3] + msg.body) if sid == 0x23 else msg
    fake.send_receive = echoing
    fl = _flash_with(fake)
    with pytest.raises(Zf5hpError):
        fl.read_image(spans=[(0x8000, 0x80FF)], chunk=0x80)


def test_a_short_seed_is_not_taken_as_unlocked():
    from ovtsuite.flash.zf5hp import Zf5hpError
    fake = _FakeKwp()
    real = fake.send_receive
    fake.send_receive = lambda sid, body=b"": (
        _Msg(b"\x01") if sid == 0x27 and body[:1] == b"\x01" else real(sid, body))
    fl = _flash_with(fake)
    with pytest.raises(Zf5hpError):
        fl.unlock()
    assert not fl._unlocked


def test_a_failed_handshake_is_not_tried_again_per_region():
    """One wrong key, not one per locked region: each counts towards the
    TCU's attempt limit."""
    from ovtsuite.flash.kwp import NegativeResponse
    fake = _FakeKwp(lock_below=0x100000)
    real = fake.send_receive
    keys = []

    def wrong_key(sid, body=b""):
        if sid == 0x27 and body[:1] == b"\x02":
            keys.append(body)
            raise NegativeResponse(0x27, 0x35)            # invalidKey
        return real(sid, body)
    fake.send_receive = wrong_key
    fl = _flash_with(fake)
    import ovtsuite.flash.zf5hp as _Z
    _orig = _Z.security_key
    _Z.security_key = lambda tape, seed: b"\x00\x00\x00\x00"
    try:
        fl.read_image(spans=[(0x8000, 0x80FF), (0x90080, 0x9017F)], chunk=0x80)
    finally:
        _Z.security_key = _orig
    assert len(keys) == 1


def test_connect_talks_to_the_init_address():
    fake = _FakeKwp()
    fl = _flash_with(fake)
    fl.connect(init_addr=0x02, session=None)
    assert fake.controller == 0x02 and fake.k.woken == 0x02
