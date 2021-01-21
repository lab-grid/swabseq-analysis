#!/usr/bin/env bash

set -e

if [[ ! -z "${BASESPACE_CFG}" ]]; then
    echo "${BASESPACE_CFG}" > /root/.basespace/default.cfg
fi

if [[ -z "${@}" ]]; then
    python3 -m gunicorn.app.wsgiapp --bind 0.0.0.0:${PORT} --workers 4 main:app
else
    ${@}
fi
