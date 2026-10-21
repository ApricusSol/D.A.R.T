#!/usr/bin/env python3
"""
Snaptain S5C Elite video stream extractor.

Connects to the drone's TCP video port, strips the custom 44-byte
per-frame header, and writes out a raw H.264 Annex-B elementary
stream that you can play with ffplay or mux into an .mp4 with ffmpeg.

Header format discovered via Wireshark capture analysis:
  offset 0-3    : 00 00 01 a0   (fixed magic)
  offset 4-9    : 00 01 00 00 00 00  (fixed)
  offset 10-11  : sequence counter (big-endian u16)
  offset 12-15  : 00 08 00 00   (fixed)
  offset 16-17  : secondary counter
  offset 18-23  : 00 00 00 00 00 00 (fixed)
  offset 24-31  : d0 02 00 05 00 00 00 00 (fixed)
  offset 32-35  : timestamp, little-endian u32 (increments ~400000/frame)
  offset 36-43  : 00000000 00000000 3a (fixed)
  offset 44-46  : 00 00 01      <- real H.264 Annex-B start code
  offset 47+    : NAL unit data

Usage:
    python3 s5c_video_extractor.py --host 192.168.10.1 --port <VIDEO_PORT> --out stream.h264

Then play/convert with:
    ffplay stream.h264
    ffmpeg -i stream.h264 -c copy stream.mp4
"""

import socket
import struct
import argparse
import sys
import time

HEADER_LEN = 44
START_CODE = b'\x00\x00\x01'
MAGIC = b'\x00\x00\x01\xa0'  # first 4 bytes of every header we've seen so far


def find_next_header(buf, start=0):
    """Find the next occurrence of the custom header's magic bytes."""
    return buf.find(MAGIC, start)


def parse_header(h):
    """Parse the 44-byte custom header. Returns dict of fields."""
    if len(h) < HEADER_LEN:
        return None
    seq = struct.unpack('>H', h[10:12])[0]
    sub = struct.unpack('>H', h[16:18])[0]
    timestamp = struct.unpack('<I', h[32:36])[0]
    return {'seq': seq, 'sub': sub, 'timestamp': timestamp}


def extract_frames(buf):
    """
    Given a buffer of accumulated TCP bytes, yield (header_info, nal_bytes)
    tuples for each complete frame found, and return the leftover
    unconsumed tail of the buffer.
    """
    frames = []
    pos = 0
    while True:
        h_start = find_next_header(buf, pos)
        if h_start == -1:
            break
        # need full header + at least the 3-byte start code to proceed
        if h_start + HEADER_LEN + 3 > len(buf):
            break

        header = buf[h_start:h_start + HEADER_LEN]
        sc_pos = h_start + HEADER_LEN
        if buf[sc_pos:sc_pos + 3] != START_CODE:
            # Header magic matched but start code didn't follow;
            # false positive match inside NAL data. Skip past it.
            pos = h_start + 4
            continue

        nal_start = sc_pos  # include the 00 00 01 start code in output
        next_h = find_next_header(buf, nal_start + 3)
        if next_h == -1:
            # Don't know where this frame ends yet; wait for more data.
            break

        nal_bytes = buf[nal_start:next_h]
        info = parse_header(header)
        frames.append((info, nal_bytes))
        pos = next_h

    leftover = buf[pos:]
    return frames, leftover


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host', required=True, help='Drone IP, e.g. 192.168.10.1')
    ap.add_argument('--port', type=int, required=True, help='Video TCP port')
    ap.add_argument('--out', default='stream.h264', help='Output file')
    ap.add_argument('--verbose', action='store_true')
    args = ap.parse_args()

    print(f"Connecting to {args.host}:{args.port} ...")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        sock.connect((args.host, args.port))
    except OSError as e:
        print(f"Connection failed: {e}", file=sys.stderr)
        sys.exit(1)
    sock.settimeout(None)
    print("Connected. Streaming... (Ctrl+C to stop)")

    buf = b''
    frame_count = 0
    last_seq = None

    with open(args.out, 'wb') as out:
        try:
            while True:
                chunk = sock.recv(65536)
                if not chunk:
                    print("Connection closed by drone.")
                    break
                buf += chunk

                frames, buf = extract_frames(buf)
                for info, nal_bytes in frames:
                    out.write(nal_bytes)
                    frame_count += 1
                    if args.verbose and info:
                        gap = ''
                        if last_seq is not None:
                            gap = f" (seq delta {info['seq'] - last_seq})"
                        print(f"frame {frame_count}: seq={info['seq']} "
                              f"ts={info['timestamp']} len={len(nal_bytes)}{gap}")
                        last_seq = info['seq']

                # Safety valve: if buffer grows unbounded without finding
                # headers, something's wrong with the framing assumption.
                if len(buf) > 10000000:
                    print("Buffer exceeded 10MB without finding a frame "
                          "boundary -- framing assumption may be wrong.",
                          file=sys.stderr)
                    break
        except KeyboardInterrupt:
            print(f"\nStopped. Wrote {frame_count} frames to {args.out}")

    sock.close()


if __name__ == '__main__':
    main()
