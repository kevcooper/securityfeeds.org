#!/usr/bin/env bash
# Prepare chrome-headless-shell for tests/mirror_column_test.py without
# installing anything system-wide.
#
# Downloads the shared libraries and fonts that chrome-headless-shell needs as
# .debs and unpacks them under $SECFEEDS_TEST_HOME (default
# ~/.cache/securityfeeds-test). Writes a fonts.conf there too. Safe to re-run:
# it does nothing if everything is already in place.
#
# Requires: Debian/Ubuntu with apt-get and dpkg, and a Playwright
# chrome-headless-shell in ~/.cache/ms-playwright (install it with
# `npx playwright install chromium-headless-shell` or set CHROME_HEADLESS_SHELL).
# If apt's package lists are empty, it runs `sudo apt-get update`, which only
# refreshes the lists and installs nothing.
#
# Prints the environment to export (tests/run.sh does this for you).
set -euo pipefail

HOME_DIR="${SECFEEDS_TEST_HOME:-$HOME/.cache/securityfeeds-test}"
ROOT="$HOME_DIR/root"
DEBS="$HOME_DIR/debs"
FC="$HOME_DIR/fontconfig"

# Package names are Debian 13 (trixie). Other releases may lack the t64 suffix.
PKGS=(
  libglib2.0-0t64 libnspr4 libnss3 libatk1.0-0t64 libatspi2.0-0t64 libdbus-1-3
  libasound2t64 libgbm1 libdrm2 libxkbcommon0
  libx11-6 libxcb1 libxau6 libxdmcp6 libxcomposite1 libxdamage1 libxext6
  libxfixes3 libxrandr2 libxrender1 libxi6
  libfontconfig1 fontconfig-config fonts-dejavu-core libfreetype6 libpng16-16t64 libbrotli1
)

log() { echo "setup-headless: $*" >&2; }

find_chrome() {
  if [[ -n "${CHROME_HEADLESS_SHELL:-}" ]]; then echo "$CHROME_HEADLESS_SHELL"; return; fi
  local c
  for c in "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux*/chrome-headless-shell; do
    [[ -x "$c" ]] && { echo "$c"; return; }
  done
  return 1
}

CHROME="$(find_chrome)" || { log "no chrome-headless-shell found; install it with Playwright or set CHROME_HEADLESS_SHELL"; exit 1; }

case "$(dpkg --print-architecture)" in
  arm64) TRIPLET=aarch64-linux-gnu ;;
  amd64) TRIPLET=x86_64-linux-gnu ;;
  *) log "unsupported architecture $(dpkg --print-architecture)"; exit 1 ;;
esac
LIBPATH="$ROOT/usr/lib/$TRIPLET:$ROOT/lib/$TRIPLET"

missing_libs() {
  LD_LIBRARY_PATH="$LIBPATH" ldd "$CHROME" | awk '/not found/ {print $1}'
  local so
  for so in "$ROOT/usr/lib/$TRIPLET"/*.so*; do
    [[ -e "$so" ]] || continue
    LD_LIBRARY_PATH="$LIBPATH" ldd "$so" 2>/dev/null | awk '/not found/ {print $1}'
  done
}

mkdir -p "$ROOT" "$DEBS" "$FC/cache"

# Download only the packages whose .deb isn't here yet.
need=()
for p in "${PKGS[@]}"; do
  compgen -G "$DEBS/${p}_*.deb" >/dev/null || need+=("$p")
done
if ((${#need[@]})); then
  if ! apt-cache show libnss3 >/dev/null 2>&1; then
    log "apt package lists are empty; running sudo apt-get update (lists only)"
    sudo apt-get update -qq
  fi
  log "downloading ${#need[@]} package(s)"
  (cd "$DEBS" && apt-get download -q "${need[@]}" >/dev/null)
fi

# Unpack each .deb once. A marker records what has been unpacked. dpkg -x
# can't create the root-owned etc/fonts/conf.d symlinks; that's harmless.
for deb in "$DEBS"/*.deb; do
  marker="$ROOT/.unpacked-$(basename "$deb")"
  [[ -e "$marker" ]] && continue
  dpkg -x "$deb" "$ROOT" 2>/dev/null || true
  touch "$marker"
done

cat > "$FC/fonts.conf" <<EOF
<?xml version="1.0"?>
<!DOCTYPE fontconfig SYSTEM "fonts.dtd">
<fontconfig>
  <dir>$ROOT/usr/share/fonts</dir>
  <cachedir>$FC/cache</cachedir>
</fontconfig>
EOF

left="$(missing_libs | sort -u)"
if [[ -n "$left" ]]; then
  log "still missing: $(echo $left)"
  log "add the packages that provide them to PKGS and re-run"
  exit 1
fi

log "ready: $CHROME"
cat <<EOF
export CHROME_HEADLESS_SHELL='$CHROME'
export LD_LIBRARY_PATH='$LIBPATH'
export FONTCONFIG_FILE='$FC/fonts.conf'
EOF
