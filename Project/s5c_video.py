#!/usr/bin/env python3
"""
s5c_video.py

One consolidated tool for the SNAPTAIN S5C Elite video pipeline, merging
what used to be three separate scripts (open_video_channel.py,
extract_h264.py, live_stream.py) into one, with three subcommands:

  live     Connect, log in on the dedicated video channel, and pipe the
           live feed straight into ffplay in real time. (Most common use.)

  capture  Connect and log in the same way, but dump the raw stream to a
           file for a fixed duration instead of displaying it live.

  extract  Post-process a raw file saved by `capture` (or `live --tee`)
           into a plain, playable .h264 file -- with diagnostic flags for
           when something looks wrong.

Background (see Walkthrough.txt Sections 5-7 for the full writeup):

  The drone's video service listens on TCP port 8866. There is NO
  separate "start play" command -- the app opens a second, DEDICATED TCP
  connection just for video, and simply logging in on that connection is
  what triggers streaming. The drone's "response to login" on this
  connection is already the first video frame, not a protocol ack.

  Each frame on the wire is a custom 44-byte header wrapping a standard
  H.264 Annex-B NAL unit. The login packet itself is a fixed envelope
  ("ITd\\0" + command byte + length field) wrapping 96 bytes of
  AES-128-ECB ciphertext, whose recovered plaintext layout encodes the
  username, password, and stream parameters (quality/encoder/blocking).

Usage:
    python3 s5c_video.py live --host 172.19.10.1 --port 8866
    python3 s5c_video.py live --host 172.19.10.1 --port 8866 --tee raw.bin
    python3 s5c_video.py capture --host 172.19.10.1 --port 8866 \\
        --out raw.bin --duration 10
    python3 s5c_video.py extract --in raw.bin --out out.h264 --debug-nals 5
"""

import argparse
import signal
import socket
import subprocess
import sys
import time

try:
    from Crypto.Cipher import AES
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


# ---------------------------------------------------------------------------
# Shared: recovered login-packet construction
# ---------------------------------------------------------------------------

AES_KEY = b"guanxukj@fh8620."  # recovered from the APK
USERNAME = b"guanxukeji"
PASSWORD = b"gxrdw60"

ENVELOPE_MAGIC = bytes.fromhex("49546400")  # "ITd\0"
ENVELOPE_CMD = bytes.fromhex("0000")
ENVELOPE_LENFIELD = (93).to_bytes(4, "little")  # observed on the video-channel login

HEADER_LEN = 44  # the custom per-frame wrapper header


def build_video_login_plaintext(purpose_byte=0x04, bt_enc_id=0x02, bt_blocked=0x01,
                                 mystery_field=0x0e):
    """
    Reconstruct the 96-byte plaintext block for a VIDEO-channel login,
    recovered by diffing a captured video-channel login against a
    captured control-channel login (see Walkthrough.txt Section 6.4):

      0x00-0x02  83 51 00          constant across both channels
      0x03       04                connection-purpose byte (0x07 seen on
                                    the control channel, 0x04 on video)
      0x04       01                constant
      0x0a-0x29  username, padded
      0x2a-0x4e  password, padded
      0x4f       0c                length of the struct that follows
      0x50-0x5b  00 00 EE BB 00 00 00 00 MM 00 00 00
                 EE = btEncID (quality/encoder: 2 seen = HD default; try 1
                      for the SD branch in the app's Java)
                 BB = btBlocked (hardcoded 1 in the app)
                 MM = unconfirmed trailing field (0x0e observed)

    bt_enc_id/bt_blocked/mystery_field are exposed so you can try
    variations (e.g. --bt-enc-id 1) if 2 doesn't give the result you want.
    """
    buf = bytearray(96)
    buf[0x00:0x03] = bytes.fromhex("835100")
    buf[0x03] = purpose_byte
    buf[0x04] = 0x01
    buf[0x0a:0x0a + len(USERNAME)] = USERNAME
    buf[0x2a:0x2a + len(PASSWORD)] = PASSWORD
    buf[0x4f] = 0x0c
    struct_block = bytes([0x00, 0x00, bt_enc_id, bt_blocked, 0x00, 0x00, 0x00, 0x00]) \
        + mystery_field.to_bytes(4, "little")
    buf[0x50:0x50 + len(struct_block)] = struct_block
    assert len(buf) == 96
    return bytes(buf)


def build_login_packet(**kwargs):
    if not HAVE_CRYPTO:
        sys.exit("ERROR: pycryptodome required. pip install pycryptodome")
    plaintext = build_video_login_plaintext(**kwargs)
    cipher = AES.new(AES_KEY, AES.MODE_ECB)
    ciphertext = cipher.encrypt(plaintext)
    return ENVELOPE_MAGIC + ENVELOPE_CMD + ENVELOPE_LENFIELD + ciphertext


# ---------------------------------------------------------------------------
# Shared: frame-boundary detection and H.264 header stripping
# ---------------------------------------------------------------------------

# Matching on the bare 3-byte "00 00 01" sync is NOT safe: a single wrapped
# frame's H.264 payload can itself contain multiple NAL units (SPS/PPS/
# slice), each with its own native Annex-B start code that also begins
# 00 00 01. We instead match the FULL combination of fields documented as
# constant across every captured frame (Walkthrough.txt Section 5.4),
# which is specific enough that it won't collide with compressed video data.

def looks_like_wrapper_header(data: bytes, pos: int) -> bool:
    if pos + HEADER_LEN > len(data):
        return False
    return (
        data[pos:pos + 3] == b"\x00\x00\x01"
        and data[pos + 4:pos + 10] == bytes.fromhex("000100000000")
        and data[pos + 12:pos + 16] == bytes.fromhex("00080000")
        and data[pos + 18:pos + 24] == bytes.fromhex("000000000000")
        and data[pos + 24:pos + 32] == bytes.fromhex("d002000500000000")
        and data[pos + 43] == 0x3a
    )


def find_frame_starts(data: bytes):
    """Every offset where a genuine wrapper-frame header begins."""
    starts = []
    i = 0
    while True:
        idx = data.find(b"\x00\x00\x01", i)
        if idx == -1:
            break
        if looks_like_wrapper_header(data, idx):
            starts.append(idx)
        i = idx + 1
    return starts


def hexdump(data: bytes, width=16):
    lines = []
    for i in range(0, len(data), width):
        chunk = data[i:i + width]
        hex_part = " ".join(f"{b:02x}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"  {i:04x}  {hex_part:<{width*3}}  {ascii_part}")
    return "\n".join(lines)


NAL_TYPE_NAMES = {
    1: "P-slice", 5: "IDR-slice", 6: "SEI", 7: "SPS", 8: "PPS",
    9: "AUD", 10: "end-of-seq", 11: "end-of-stream", 12: "filler",
}


def find_nal_starts(payload: bytes):
    starts = []
    i = 0
    while True:
        idx = payload.find(b"\x00\x00\x01", i)
        if idx == -1:
            break
        starts.append(idx + 3)
        i = idx + 3
    return starts


def describe_nals(payload: bytes):
    starts = find_nal_starts(payload)
    if not starts:
        return []
    results = []
    for n, s in enumerate(starts):
        if s >= len(payload):
            continue
        nal_type = payload[s] & 0x1F
        end = starts[n + 1] - 3 if n + 1 < len(starts) else len(payload)
        results.append((nal_type, max(end - s, 0)))
    return results


# ---------------------------------------------------------------------------
# Connection helper shared by `live` and `capture`
# ---------------------------------------------------------------------------

def connect_and_login(host, port, bt_enc_id, connect_timeout):
    packet = build_login_packet(bt_enc_id=bt_enc_id)
    print(f"Connecting to {host}:{port} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(connect_timeout)
    try:
        sock.connect((host, port))
    except OSError as e:
        sys.exit(f"ERROR: could not connect: {e}")
    print("Connected. Sending video-channel login packet ...")
    sock.sendall(packet)
    return sock


# ---------------------------------------------------------------------------
# Subcommand: live
# ---------------------------------------------------------------------------

def cmd_live(args):
    sock = connect_and_login(args.host, args.port, args.bt_enc_id, args.connect_timeout)
    sock.settimeout(1.0)

    print("Starting ffplay (reading raw H.264 from stdin) ...")
    try:
        ffplay = subprocess.Popen(
            ["ffplay", "-f", "h264", "-probesize", "32", "-analyzeduration", "0",
             "-fflags", "nobuffer", "-flags", "low_delay", "-framedrop",
             "-i", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        sys.exit("ERROR: ffplay not found on PATH (part of ffmpeg).")

    tee_file = open(args.tee, "wb") if args.tee else None

    buf = b""
    total_frames = 0
    stop = {"flag": False}

    def handle_sigint(signum, frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, handle_sigint)

    print("Streaming -- Ctrl-C to stop.")
    try:
        while not stop["flag"]:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                print("Connection closed by drone.")
                break

            if tee_file:
                tee_file.write(chunk)

            buf += chunk

            # Emit every complete frame currently in the buffer. We only
            # know a frame is complete once we see the START of the NEXT
            # frame, so we always keep the final (possibly still-arriving)
            # frame buffered rather than emitting it.
            starts = find_frame_starts(buf)
            while len(starts) >= 2:
                frame = buf[starts[0]:starts[1]]
                if len(frame) > HEADER_LEN:
                    try:
                        ffplay.stdin.write(frame[HEADER_LEN:])
                        ffplay.stdin.flush()
                    except (BrokenPipeError, OSError):
                        print("ffplay closed its input -- stopping.")
                        stop["flag"] = True
                        break
                    total_frames += 1
                buf = buf[starts[1]:]
                starts = find_frame_starts(buf)

            if len(buf) > 2_000_000:
                print("WARNING: buffer exceeded 2MB without finding a frame "
                      "boundary -- dropping buffered data. Save a copy with "
                      "--tee and check it with `extract --debug-nals` if "
                      "this keeps happening.")
                buf = b""
    except KeyboardInterrupt:
        pass
    finally:
        print(f"\nStopping. Wrote {total_frames} frame(s) to ffplay.")
        try:
            ffplay.stdin.close()
        except Exception:
            pass
        sock.close()
        if tee_file:
            tee_file.close()
        ffplay.terminate()


# ---------------------------------------------------------------------------
# Subcommand: capture
# ---------------------------------------------------------------------------

def cmd_capture(args):
    sock = connect_and_login(args.host, args.port, args.bt_enc_id, args.connect_timeout)

    sock.settimeout(2.0)
    login_response = b""
    try:
        login_response = sock.recv(4096)
        print(f"Got {len(login_response)}-byte response to login.")
    except socket.timeout:
        print("No response to login within 2s -- continuing to listen anyway.")

    print(f"Listening for up to {args.duration}s, writing raw bytes to {args.out} ...")
    sock.settimeout(1.0)
    total_bytes = 0
    saw_video_magic = False
    deadline = time.monotonic() + args.duration

    with open(args.out, "wb") as f:
        # IMPORTANT: on this drone the "response to login" above IS already
        # live video data -- there is no separate ack -- so it must be
        # written to the file too. Earlier versions of this tooling
        # discarded it, which left every capture missing its own first
        # SPS/PPS/IDR frame (see Walkthrough.txt Section 7.1).
        if login_response:
            f.write(login_response)
            total_bytes += len(login_response)
            if b"\x00\x00\x01\xa0" in login_response or b"\x00\x00\x01\xa1" in login_response:
                saw_video_magic = True
                print("  [OK] Video frame magic was already present in the "
                      "login response -- written to the output file.")

        while time.monotonic() < deadline:
            try:
                chunk = sock.recv(65536)
            except socket.timeout:
                continue
            if not chunk:
                print("Connection closed by drone.")
                break
            f.write(chunk)
            total_bytes += len(chunk)
            if not saw_video_magic and (b"\x00\x00\x01\xa0" in chunk or b"\x00\x00\x01\xa1" in chunk):
                saw_video_magic = True
                print("  [OK] Video frame magic seen in the stream.")

    sock.close()
    print(f"\nDone. {total_bytes} bytes written to {args.out}.")
    if saw_video_magic:
        print(f"Run: python3 {sys.argv[0]} extract --in {args.out} --out out.h264")
    elif total_bytes == 0:
        print("No bytes received at all -- check connectivity (ping the "
              "drone, confirm you're associated to its WiFi), or try "
              "--bt-enc-id 1.")
    else:
        print("Bytes were received but no video magic was seen in this "
              "window -- inspect the file directly, or try --bt-enc-id 1.")


# ---------------------------------------------------------------------------
# Subcommand: extract
# ---------------------------------------------------------------------------

def cmd_extract(args):
    with open(args.infile, "rb") as f:
        data = f.read()

    print(f"Read {len(data)} bytes from {args.infile}")

    all_starts = find_frame_starts(data)
    if not all_starts:
        sys.exit("No frame markers found at all -- wrong input file, or "
                  "the capture didn't actually contain video.")

    print(f"Found {len(all_starts)} frame marker(s)")

    frame_spans = [
        (s, all_starts[i + 1] if i + 1 < len(all_starts) else len(data))
        for i, s in enumerate(all_starts)
    ]

    if args.start_at_keyframe > 1:
        keyframe_starts = [s for s in all_starts if data[s + 3] == 0xa1]
        print(f"Found {len(keyframe_starts)} keyframe(s) (type 0xa1).")
        if len(keyframe_starts) < args.start_at_keyframe:
            sys.exit(f"Only {len(keyframe_starts)} keyframe(s) found -- "
                      f"can't start at keyframe {args.start_at_keyframe}.")
        skip_before = keyframe_starts[args.start_at_keyframe - 1]
        skipped = sum(1 for s, _ in frame_spans if s < skip_before)
        frame_spans = [(s, e) for s, e in frame_spans if s >= skip_before]
        print(f"Skipping {skipped} frame(s) before keyframe "
              f"#{args.start_at_keyframe} (offset {skip_before}).")

    frame_count = 0
    total_payload = 0
    with open(args.outfile, "wb") as out:
        for start, end in frame_spans:
            frame = data[start:end]
            if len(frame) <= HEADER_LEN:
                continue  # stray match inside compressed data, not a real frame
            frame_type = frame[3]
            payload = frame[HEADER_LEN:]
            out.write(payload)
            total_payload += len(payload)
            frame_count += 1
            if frame_count <= 5 or frame_count % 50 == 0:
                print(f"  frame {frame_count}: offset={start} type=0x{frame_type:02x} "
                      f"total_len={len(frame)} payload_len={len(payload)}")

            if frame_count <= args.debug_nals:
                if not HAVE_CRYPTO:
                    pass  # NAL debug doesn't need crypto, always available
                nals = describe_nals(payload)
                if not nals:
                    print(f"    [debug] no Annex-B start code in this payload "
                          f"-- first bytes: {payload[:16].hex()}")
                else:
                    for nal_type, size in nals:
                        name = NAL_TYPE_NAMES.get(nal_type, f"type={nal_type}")
                        print(f"    [debug] NAL: {name:<14} size={size}")

    print(f"\nWrote {frame_count} frame(s), {total_payload} bytes of payload, "
          f"to {args.outfile}")
    print(f"\nTry: ffplay {args.outfile}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)

    common = dict(add_help=False)

    p_live = sub.add_parser("live", help="Stream live video straight into ffplay",
                             description=cmd_live.__doc__)
    p_live.add_argument("--host", default="172.19.10.1")
    p_live.add_argument("--port", type=int, default=8866)
    p_live.add_argument("--bt-enc-id", type=int, default=2, choices=[1, 2],
                         help="Quality/encoder selector recovered from the "
                              "login packet (2=default/HD branch, 1=SD "
                              "branch in the app's Java). Try 1 if 2 "
                              "doesn't work.")
    p_live.add_argument("--tee", default=None,
                         help="Also save the raw (undeframed) stream to "
                              "this file while playing live.")
    p_live.add_argument("--connect-timeout", type=float, default=5.0)
    p_live.set_defaults(func=cmd_live)

    p_capture = sub.add_parser("capture", help="Dump raw video to a file for N seconds",
                                description=cmd_capture.__doc__)
    p_capture.add_argument("--host", default="172.19.10.1")
    p_capture.add_argument("--port", type=int, default=8866)
    p_capture.add_argument("--bt-enc-id", type=int, default=2, choices=[1, 2])
    p_capture.add_argument("--out", default="raw_video_stream.bin")
    p_capture.add_argument("--duration", type=float, default=5.0)
    p_capture.add_argument("--connect-timeout", type=float, default=5.0)
    p_capture.set_defaults(func=cmd_capture)

    p_extract = sub.add_parser("extract", help="Convert a raw dump into playable .h264",
                                description=cmd_extract.__doc__)
    p_extract.add_argument("--in", dest="infile", required=True)
    p_extract.add_argument("--out", dest="outfile", default="out.h264")
    p_extract.add_argument("--debug-nals", type=int, default=0, metavar="N",
                            help="Print NAL-type breakdown for the first N "
                                 "frames (diagnose decode errors).")
    p_extract.add_argument("--start-at-keyframe", type=int, default=1, metavar="K",
                            help="Skip everything before the Kth keyframe "
                                 "(type 0xa1). Use if an early GOP is "
                                 "corrupt but later ones play fine.")
    p_extract.set_defaults(func=cmd_extract)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
