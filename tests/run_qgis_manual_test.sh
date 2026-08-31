#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_PARENT="$(dirname "${PLUGIN_DIR}")"
TEST_ROOT="/private/tmp/line-profile-qgis-manual"
QGIS_APP="/Applications/QGIS.app/Contents/MacOS/QGIS"

if [[ ! -x "${QGIS_APP}" ]]; then
    echo "QGIS was not found at ${QGIS_APP}" >&2
    exit 1
fi

mkdir -p "${TEST_ROOT}/matplotlib"
export QGIS_PLUGINPATH="${PLUGIN_PARENT}"
export MPLCONFIGDIR="${TEST_ROOT}/matplotlib"

exec "${QGIS_APP}" \
    --profiles-path "${TEST_ROOT}" \
    --profile codex-line-profile \
    --code "${SCRIPT_DIR}/manual_qgis_startup.py" \
    --nologo \
    --noversioncheck
