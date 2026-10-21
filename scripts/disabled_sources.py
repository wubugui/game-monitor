#!/usr/bin/env python3
"""DEPRECATED: former notes-app discovery permanently disabled.

Channels are Bilibili / X / Steam only. This module is a no-op kept so old
imports and publish path listings do not break. Do not re-enable scraping.
"""
import sys

def main():
    print('legacy notes-app sources: disabled (channels: Bilibili / X / Steam only)', file=sys.stderr)
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
