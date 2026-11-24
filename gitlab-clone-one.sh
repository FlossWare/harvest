#!/bin/bash
# gitlab-clone-one.sh <group/project> <dirname> — shallow-clone one repo
# over SSH, skip if present. Built for `xargs -P` parallel sweeps.
#
# Env:
#   GITLAB_HOST  GitLab SSH host (default: gitlab.com)
#   REPOS_DIR    destination dir (default: ~/corpus/gitlab-repos)
path="$1"; dir="$2"
[ -z "$path" ] || [ -z "$dir" ] && { echo "usage: gitlab-clone-one.sh <group/project> <dirname>"; exit 1; }
host="${GITLAB_HOST:-gitlab.com}"
repos="${REPOS_DIR:-$HOME/corpus/gitlab-repos}"
mkdir -p "$repos"
cd "$repos" || exit 1
[ -d "$dir" ] && { echo "SKIP $dir"; exit 0; }
git clone -q --depth 1 "git@${host}:${path}.git" "$dir" && echo "OK $dir" || echo "FAIL $path"
