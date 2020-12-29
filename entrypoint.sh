#!/usr/bin/env sh

set -e

if [ ! -z "${BASESPACE_CFG}" ]; then
    echo "${BASESPACE_CFG}" > /root/.basespace/default.cfg
fi

${@}
