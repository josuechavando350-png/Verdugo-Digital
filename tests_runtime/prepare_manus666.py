"""Explicit original-source preparation, never called by Engine."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def prepare(prefix):
    raise RuntimeError('OpenManus preparation blocked: mandatory html2text GPL-3.0; see contracts-executive-blockers666.json')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--prefix', default=sys.prefix)
    prepare(parser.parse_args().prefix)
