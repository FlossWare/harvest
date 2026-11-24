#!/usr/bin/env python3
"""Send a Wake-on-LAN magic packet. Usage: wake.py <mac> [broadcast_ip]

MAC formats accepted: 00:19:b9:1f:34:b6, 00-19-b9-1f-34-b6, 0019b91f34b6
Defaults to 255.255.255.255 broadcast.
"""
import socket
import sys


def wake(mac, broadcast="255.255.255.255"):
    mac = mac.replace(":", "").replace("-", "").strip()
    if len(mac) != 12:
        sys.exit(f"bad MAC: {mac!r}")
    packet = bytes.fromhex("FF" * 6 + mac * 16)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(packet, (broadcast, 9))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: wake.py <mac> [broadcast_ip]")
    wake(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "255.255.255.255")
    print(f"sent magic packet to {sys.argv[1]}")
