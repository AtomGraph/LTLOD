#!/usr/bin/env bash
# Recursively PUT every *.ttl in a folder tree as a LinkedDataHub document:
# <folder>/foo.ttl -> ${base}foo/ (path = file path minus $pwd prefix and
# extension, plus trailing slash). Simplified from linkeddatahub.com's
# update-folder.sh: TTL documents only, no file uploads. A folder's .ttl files
# are processed before its subdirectories, so parent containers always exist
# before their children (taxonomies.ttl before taxonomies/*.ttl).
set -e

if [ "$#" -ne 5 ] && [ "$#" -ne 6 ]; then
  echo "Usage:   $0" '$base $cert_pem_file $cert_password $pwd $abs_folder [$proxy]' >&2
  echo "Example: $0" 'https://localhost:4443/ ./ssl/owner/cert.pem Password /folder /folder [https://localhost:5443/]' >&2
  echo "Note: special characters such as $ need to be escaped in passwords!" >&2
  exit 1
fi

base="$1"
cert_pem_file="$2"
cert_password="$3"
pwd="$4"
folder="$5"
proxy="${6:-$base}"

ldhignore_file="$folder/.ldhignore"

is_ldhignored() {
    local name
    name="$(basename "$1")"
    [[ -f "$ldhignore_file" ]] || return 1
    while IFS= read -r pattern || [[ -n "$pattern" ]]; do
        [[ -z "$pattern" || "$pattern" == \#* ]] && continue
        pattern="${pattern%/}"
        [[ "$name" == $pattern ]] && return 0
    done < "$ldhignore_file"
    return 1
}

for ttl_file in "$folder"/*.ttl; do
  if [[ -f "$ttl_file" ]]; then
    if git check-ignore -q "$ttl_file" 2>/dev/null || is_ldhignored "$ttl_file"; then
      printf "Skipping %s\n" "$ttl_file"
      continue
    fi
    path="${ttl_file%.*}"   # strip extension
    path="${path#*$pwd/}"   # strip leading $pwd/
    path="${path}/"         # add trailing slash
    printf "\n### Updating %s\n" "${base}${path}"
    cat "$ttl_file" | turtle --base="${base}${path}" | put.sh \
      -f "$cert_pem_file" \
      -p "$cert_password" \
      --proxy "$proxy" \
      -t "application/n-triples" \
      "${base}${path}"
  fi
done

while IFS= read -r subdir; do
  if git check-ignore -q "$subdir" 2>/dev/null || is_ldhignored "$subdir"; then
    printf "Skipping %s\n" "$subdir"
    continue
  fi
  "$(dirname "$0")/update-folder.sh" "$base" "$cert_pem_file" "$cert_password" "$pwd" "$subdir" "$proxy"
done < <(find "$folder" -mindepth 1 -maxdepth 1 -type d -not -name '.*' -not -name 'target')
