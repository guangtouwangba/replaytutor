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

if git ls-files | rg '\.(db|sqlite|log)$|(^|/)(auth\.json|credentials\.json)$'; then
  echo "release scan: tracked database, log, or credential file found" >&2
  exit 1
fi

if git ls-files | rg --pcre2 '(^|/)\.env(?!\.example$)'; then
  echo "release scan: tracked database, log, or credential file found" >&2
  exit 1
fi

for screenshot_candidate in $(git ls-files 'docs/screenshots/**' | rg -i '(^|/)[^/]*settings[^/]*\.(png|jpe?g|webp)$' || true); do
  if [[ -f "$screenshot_candidate" ]]; then
    echo "release scan: settings screenshot may expose local paths: $screenshot_candidate" >&2
    exit 1
  fi
done

if git grep -IlE \
  '/Users/|/home/[^/]+/|BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY|AKIA[A-Z0-9]{16}|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}' \
  -- . ':(exclude)scripts/check-release-artifacts.sh'; then
  echo "release scan: tracked local path or secret-like material found" >&2
  exit 1
fi

echo "release artifacts and tracked files contain no local paths, databases, logs, or secret patterns"
