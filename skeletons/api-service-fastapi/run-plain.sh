#!/usr/bin/env bash
set -e

SCRIPTPATH="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

if [ -z ${VIRTUAL_ENV+x} ]; then
  . "${SCRIPTPATH}"/.venv/bin/activate
else
  if [ ! "${VIRTUAL_ENV}" = "${SCRIPTPATH}/.venv" ]; then
    >&2 echo "WARNING: Running this script from inside a non-standard virtual environment!" 
  fi
fi

fastapi dev main.py ${@}
