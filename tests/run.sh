#!/usr/bin/env bash
# One command to run the mirror-column DOM test:
#   tests/run.sh
# Sets up chrome-headless-shell's libraries if needed (tests/setup-headless.sh),
# then runs tests/mirror_column_test.py against docs/.
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
eval "$("$here/setup-headless.sh")"
exec python3 -I "$here/mirror_column_test.py" "$here/../docs" "$CHROME_HEADLESS_SHELL"
