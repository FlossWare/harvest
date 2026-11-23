#!/bin/bash
# clone-one.sh <owner/repo> <dirname>  — shallow clone one repo, skip if present
repo="$1"; dir="$2"
cd ~/.FlossWare/sources/web-scrape/repos || exit 1
if [ -d "$dir" ]; then echo "SKIP $dir"; exit 0; fi
git clone --depth 1 -q "https://github.com/$repo" "$dir" && echo "OK $dir" || echo "FAIL $repo"
