#!/bin/bash

set -e
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"
pushd "${HERE}"

REQUIREMENTS=requirements.txt
PLATFORMS=(manylinux1_x86_64 macosx_10_6_intel win32 win_amd64)
PYTHON_VERSIONS=(2.7 3.6 3.7)
FONTMAKE_VERSION="$(python setup.py --version)"

mkdir -p shivs

for platform in ${PLATFORMS[*]}; do
    for version in ${PYTHON_VERSIONS[*]}; do
        v=${version//.}
        if [[ $v == 27 ]] && [[ $platform == manylinux1_x86_64 ]]; then
            abi="cp${v}mu"
        else
            abi="cp${v}m"
        fi
        shiv -c fontmake \
             -o shivs/fontmake-${FONTMAKE_VERSION}-cp${v}-${abi}-${platform}.pyz \
             -p "/usr/bin/env python${version}" \
             --python-version ${v} \
             --platform ${platform} \
             --abi ${abi} \
             --implementation cp \
             --only-binary=:all: \
             -r "${REQUIREMENTS}" \
             dist/fontmake-"${FONTMAKE_VERSION}"-py2.py3-none-any.whl
    done
done

popd
