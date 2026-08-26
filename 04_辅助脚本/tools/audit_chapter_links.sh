#!/usr/bin/env bash
set -euo pipefail

root="$(cd "$(dirname "$0")/.." && pwd)"
output="$root/records/publication_link_audit.log"
tmp_urls="$(mktemp)"
trap 'rm -f "$tmp_urls"' EXIT

# 提取 Markdown 可见 URL；反引号、引号、中文标点和右括号不属于 URL。
grep -rhoE 'https?://[^ <>()]+' "$root/chapters"/*.md \
  | tr -d '\`"' \
  | sed -E 's/[.,;:，。；：、]+$//' \
  | sort -u > "$tmp_urls"

{
  echo '# Chapter reference link audit'
  echo "# Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  echo '# Classification: reachable (2xx/3xx); access-restricted (public page blocks automated HTTP); illustrative (local/example URL, not fetched).'
  printf '%-18s %s\n' 'classification' 'url'
  while IFS= read -r url; do
    case "$url" in
      http://127.0.0.1:*|http://localhost:*|https://api.example.com*|https://other.example.test*)
        printf '%-18s %s\n' 'illustrative' "$url"
        continue
        ;;
    esac
    status="$(curl -L -I --max-time 12 --connect-timeout 5 -A 'Mozilla/5.0 (compatible; course-link-audit/1.0)' -s -o /dev/null -w '%{http_code}' "$url" || true)"
    if [[ "$status" == "000" ]]; then
      status="$(curl -L --max-time 12 --connect-timeout 5 -A 'Mozilla/5.0 (compatible; course-link-audit/1.0)' -s -o /dev/null -w '%{http_code}' "$url" || true)"
    fi
    case "$status" in
      200|201|202|204|301|302|303|307|308) classification='reachable' ;;
      401|403|429) classification='access-restricted' ;;
      *) classification="unreachable-$status" ;;
    esac
    printf '%-18s %s\n' "$classification" "$url"
  done < "$tmp_urls"
} | tee "$output"

awk 'NR > 3 && $1 ~ /^unreachable-/ {bad=1; print "UNREACHABLE:", $0} END {exit bad}' "$output"
