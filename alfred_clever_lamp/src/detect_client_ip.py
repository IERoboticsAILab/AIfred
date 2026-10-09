#!/usr/bin/env python3
"""Resolve the local IPv4 address for NatNet before its node starts."""

import argparse
import socket
import sys


def resolve_client_ip(server, port, client="auto"):
    if client != "auto":
        return client
    # UDP connect only selects a route; it does not send packets to the server.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect((server, port))
        return sock.getsockname()[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--server", required=True)
    parser.add_argument("--port", type=int, default=1510)
    parser.add_argument("--client", default="auto")
    args = parser.parse_args()
    try:
        # roslaunch preserves command output, including any trailing newline.
        sys.stdout.write(resolve_client_ip(args.server, args.port, args.client))
    except OSError as exc:
        print(
            "Cannot detect NatNet client IP: {}. "
            "Check the network or launch with clientIP:=<local IPv4 address>.".format(exc),
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
