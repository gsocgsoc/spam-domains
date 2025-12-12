#!/usr/bin/env python3

import argparse
import hashlib
import os
import re
import sys
import urllib.request
from typing import Iterable, Iterator, List, Optional, Set


_DOMAIN_RE = re.compile(r"^(?:\*\.)?(?=.{1,253}$)(?!-)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def _is_ip(s: str) -> bool:
    parts = s.split(".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    return all(0 <= n <= 255 for n in nums)


def _normalize_domain(raw: str) -> Optional[str]:
    s = raw.strip().lower()

    if not s:
        return None

    s = s.strip("\"' ")

    if s.startswith("http://") or s.startswith("https://"):
        s = re.sub(r"^https?://", "", s)
        s = s.split("/", 1)[0]

    s = s.split(":", 1)[0]

    if s.startswith("||"):
        s = s[2:]
    if s.startswith("."):
        s = s[1:]
    if s.startswith("*."):
        s = s[2:]
    if s.endswith("^"):
        s = s[:-1]

    s = s.strip(".")

    if not s or _is_ip(s):
        return None

    try:
        s = s.encode("idna").decode("ascii")
    except Exception:
        return None

    if not _DOMAIN_RE.match(s):
        return None

    return s


def _extract_domains_from_line(line: str) -> Iterator[str]:
    s = line.strip()
    if not s:
        return

    if s.startswith("#") or s.startswith("//"):
        return

    s = re.split(r"\s+#", s, maxsplit=1)[0].strip()

    if not s:
        return

    if "0.0.0.0" in s or "127.0.0.1" in s or "::1" in s:
        tokens = s.split()
        for tok in tokens:
            d = _normalize_domain(tok)
            if d:
                yield d
        return

    tokens = re.split(r"\s+", s)
    for tok in tokens:
        d = _normalize_domain(tok)
        if d:
            yield d


def _read_sources_file(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8") as f:
        out: List[str] = []
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            out.append(s)
        return out


def _fetch_url(url: str, timeout_seconds: int) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "spam-domains-updater/1.0 (+https://github.com)",
            "Accept": "text/plain,*/*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        data = resp.read()

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("latin-1")


def _sha256_text(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8", errors="replace")).hexdigest()


def _write_output(path: str, domains: Iterable[str]) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        for d in domains:
            f.write(d)
            f.write("\n")
    os.replace(tmp, path)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="spamdomains.txt")
    parser.add_argument("--sources-file", default="sources.txt")
    parser.add_argument("--source", action="append", default=[])
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args(argv)

    sources: List[str] = []

    if args.sources_file and os.path.exists(args.sources_file):
        sources.extend(_read_sources_file(args.sources_file))

    if args.source:
        sources.extend(args.source)

    if not sources:
        print("No sources provided. Add URLs to sources.txt or pass --source.", file=sys.stderr)
        return 2

    domains: Set[str] = set()

    for url in sources:
        text = _fetch_url(url, timeout_seconds=args.timeout)
        for line in text.splitlines():
            for d in _extract_domains_from_line(line):
                domains.add(d)

    ordered = sorted(domains)

    before = ""
    if os.path.exists(args.output):
        with open(args.output, "r", encoding="utf-8", errors="replace") as f:
            before = f.read()

    after = "\n".join(ordered) + ("\n" if ordered else "")

    if _sha256_text(before) != _sha256_text(after):
        _write_output(args.output, ordered)
        print(f"Updated {args.output}: {len(ordered)} domains")
    else:
        print(f"No changes: {args.output}: {len(ordered)} domains")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
