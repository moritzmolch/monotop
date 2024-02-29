#!/usr/bin/env bash


action () {
  local shell_is_zsh="$( [ -z "${ZSH_VERSION}" ] && echo "false" || echo "true" )"
  local this_file="$( ${shell_is_zsh} && echo "${(%):-%x}" || echo "${BASH_SOURCE[0]}" )"
  local this_dir="$( cd "$( dirname "${this_file}" )" && pwd )"

  source "/cvmfs/sft.cern.ch/lcg/views/LCG_105/x86_64-centos7-gcc12-opt/setup.sh"

  export PYTHONPATH="${this_dir}:${PYTHONPATH}"
}


action "$@"
