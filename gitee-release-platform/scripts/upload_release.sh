#!/usr/bin/env bash
# Upload a release APK to a public Gitee repo's Release (app in-app update channel).
#
# Convention (parsed by the backend /api/app/release/ reference parser):
#     tag = v<versionName>   the full version string itself (git-derived at build time)
#     .apk attachment        renamed <ATTACH_PREFIX>-<versionName>.apk on Gitee
#     body                   update notes, forwarded verbatim
#
# Usage (Git Bash / any POSIX shell):
#     GITEE_TOKEN=<pat> RELEASE_REPO='<owner>/<repo>' \
#     bash upload_release.sh <apk-path> <versionName> [notes]
#
# Environment:
#     GITEE_TOKEN          (required) personal access token, projects scope
#     RELEASE_REPO         (required) '<owner>/<repo>', public repo initialized with a README;
#                          BABY_RELEASE_REPO accepted as fallback (legacy project habit)
#     ATTACH_PREFIX        attachment name prefix, default 'app' (宝宝助手 uses 'baby')
#     RELEASE_SERVER_HOST  optional host:port of the backend serving /api/app/release/;
#                          when set, the script prints the endpoint's parsed output as a
#                          final check ('?fresh=1', bypasses server-side cache)
#
# Existing tag -> abort (bump version or delete that Release first; delete also
# removes the tag, then re-run this script). See references/gitee-api-pitfalls.md
# for the Gitee quirks this script works around.
set -euo pipefail

APK="${1:?usage: upload_release.sh <apk-path> <versionName> [notes]}"
VNAME="${2:?missing versionName}"
NOTES="${3:-}"
REPO="${RELEASE_REPO:-${BABY_RELEASE_REPO:-}}"
REPO="${REPO:?set RELEASE_REPO=<owner>/<repo> (public gitee release repo, README-initialized)}"
TOKEN="${GITEE_TOKEN:?set GITEE_TOKEN=<personal access token, projects scope>}"

[ -f "$APK" ] || { echo "ERROR: apk not found: $APK" >&2; exit 1; }
FILENAME=$(basename "$APK")
ATTACH_PREFIX="${ATTACH_PREFIX:-app}"
DL_NAME="$ATTACH_PREFIX-$VNAME.apk"   # matches the on-device download save name convention
TAG="v$VNAME"
API="https://gitee.com/api/v5/repos/$REPO"

# Gitee quirk: missing tag returns HTTP 200 with body "null" -> json.load gives
# None, .get() would crash under set -e; tolerate null/empty/non-dict responses
json_field() { python -c "import json,sys
try: d = json.load(sys.stdin)
except Exception: d = None
print(d.get('$1','') if isinstance(d, dict) else '')"; }

# 1) create the release (abort on existing tag: re-uploading would duplicate assets)
exist=$(curl -s --max-time 15 "$API/releases/tags/$TAG?access_token=$TOKEN")
if [ "$(echo "$exist" | json_field tag_name)" = "$TAG" ]; then
    echo "ERROR: release tag $TAG already exists in $REPO." >&2
    echo "       bump the version, or delete that release on gitee.com first." >&2
    exit 1
fi

# build the create-release payload as an ASCII-safe JSON file: Chinese notes
# must not ride through native curl argv on Windows (GBK console), and JSON
# files dodge all of it. Real newlines here; json.dumps escapes them.
# target_commitish is REQUIRED when the tag doesn't exist yet (Gitee refuses to
# guess the default branch); resolve it from the repo instead of hardcoding.
DBRANCH=$(curl -s --max-time 15 "$API?access_token=$TOKEN" | json_field default_branch)
DBRANCH="${DBRANCH:-master}"
BODY_FILE=".release-body.$$.txt"; PAYLOAD=".release-payload.$$.json"
trap 'rm -f "$BODY_FILE" "$PAYLOAD"' EXIT
printf '%s' "$NOTES" > "$BODY_FILE"
python -c "import json;json.dump({'tag_name':'$TAG','name':'$TAG','prerelease':False,'target_commitish':'$DBRANCH','body':open(r'$BODY_FILE',encoding='utf-8').read()},open(r'$PAYLOAD','w'),ensure_ascii=True)"
rel=$(curl -s --max-time 20 -X POST "$API/releases?access_token=$TOKEN" \
      -H 'Content-Type: application/json' --data-binary @"$PAYLOAD")
rid=$(echo "$rel" | json_field id)
[ -n "$rid" ] || { echo "ERROR: create release failed: $rel" >&2; exit 1; }
echo "== release $TAG created (id=$rid, version=$VNAME)"

# 2) upload the apk as release attachment (Gitee expects form field "file";
#    ;filename= renames the attachment, keeping the local product name untouched)
echo "== uploading $FILENAME (as $DL_NAME) ..."
up=$(curl -s --max-time 600 -X POST "$API/releases/$rid/attach_files?access_token=$TOKEN" \
     -F "file=@$APK;filename=$DL_NAME")
url=$(echo "$up" | json_field browser_download_url)
url="${url:-https://gitee.com/$REPO/releases/download/$TAG/$DL_NAME}"

# 3) smoke checks: public direct link must resolve (anonymous, like the app does)
code=$(curl -s -o /dev/null -w '%{http_code}' -I -L --max-time 30 "$url" || true)
echo "HEAD $TAG/$DL_NAME -> $code (expect 200)"
[ "$code" = "200" ] || { echo "direct-link smoke FAILED" >&2; exit 1; }

# 4) optional: confirm the backend exposes the fresh release (set RELEASE_SERVER_HOST)
CHECK_HOST="${RELEASE_SERVER_HOST:-}"
if [ -n "$CHECK_HOST" ]; then
    resp=$(curl -s --max-time 15 "http://$CHECK_HOST/api/app/release/?fresh=1" || true)
    if [ -n "$resp" ]; then
        echo "== server /api/app/release/ -> $resp"
    else
        echo "WARN: server /api/app/release/ returned 204/empty." >&2
        echo "      check APP_RELEASE_GITEE_REPO on the server side ($CHECK_HOST)." >&2
    fi
fi
echo "== OK  apk published: $url"
