#!/bin/bash
set -euo pipefail

dist_dir="apps/web/dist"
if [[ ! -d "$dist_dir" ]]; then
  echo "release scan: missing $dist_dir" >&2
  exit 1
fi

if find "$dist_dir" -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.log' \) -print -quit | grep -q .; then
  echo "release scan: database or log file found in web build" >&2
  exit 1
fi

if rg -l '/Users/|/home/[^/]+/|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|api[_-]?secret|secret[_-]?key' "$dist_dir"; then
  echo "release scan: local path or secret-like material found" >&2
  exit 1
fi

echo "release artifacts contain no local paths, databases, logs, or secret patterns"
