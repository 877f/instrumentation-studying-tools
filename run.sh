#!/usr/bin/env bash
# Run the study tool on this computer, for testing changes before they go live (Linux and macOS).
#
#   ./run.sh                start it and open http://localhost:5000 in your browser
#   ./run.sh --port 5050    use another port
#   ./run.sh test           run the test suites
#
# The first run creates .venv/ and installs requirements.txt into it. Pages reload by
# themselves when you save a file, and phones on the same Wi-Fi can open the address it
# prints. Ctrl+C stops it.
set -euo pipefail
cd "$(dirname "$0")"

PY=$(command -v python3 || command -v python || true)
if [ -z "$PY" ]; then
  echo "Python 3 isn't installed. Get it from https://www.python.org/downloads/ or your package manager." >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting up .venv ..."
  if ! "$PY" -m venv .venv; then
    rm -rf .venv
    echo "Couldn't create .venv. On Debian or Ubuntu, install it with: sudo apt install python3-venv" >&2
    exit 1
  fi
fi
if [ ! -f .venv/.installed ] || [ requirements.txt -nt .venv/.installed ]; then
  .venv/bin/python -m pip install --quiet --disable-pip-version-check -r requirements.txt
  touch .venv/.installed
fi

if [ "${1:-}" = "test" ]; then
  for t in test_app.py test_wheel.py test_worksheet.py test_problems.py test_study.py; do
    echo "== $t"
    .venv/bin/python "$t"
  done
  exit 0
fi
exec .venv/bin/python app.py --dev --open "$@"
