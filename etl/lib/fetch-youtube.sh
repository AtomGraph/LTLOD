#!/usr/bin/env bash
# List a YouTube channel's videos and live streams (id + title) as CSV, and fail loudly
# on an empty listing. yt-dlp's flat listing needs no API key; it runs via uvx at the
# latest release, since YouTube changes break older ones.
# Usage: fetch-youtube.sh <channel-url> <output.csv>
set -euo pipefail

channel="$1"
out="$2"

mkdir -p "$(dirname "$out")"
tmp="$(mktemp -t fetch-youtube.XXXXXX)"
trap 'rm -f "$tmp"' EXIT

for tab in streams videos; do
    uvx yt-dlp@latest --quiet --no-warnings --flat-playlist \
        --print '%(id)s	%(title)s' "${channel%/}/$tab" >> "$tmp"
done

# a video can appear on both tabs; titles have no tabs but may carry quotes
{
    echo 'video_id,title'
    awk -F'\t' '!seen[$1]++ { gsub(/"/, "\"\"", $2); printf "%s,\"%s\"\n", $1, $2 }' "$tmp"
} > "${out}.tmp"

count=$(($(wc -l < "${out}.tmp") - 1))
if [ "$count" -eq 0 ]; then
    echo "ERROR: ${channel} listed no videos" >&2
    rm -f "${out}.tmp"
    exit 1
fi

mv "${out}.tmp" "$out"
echo "fetched ${channel}: ${count} videos -> ${out}" >&2
