#!/bin/bash

set -e
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

PLATFORMS=(macosx_11_0_universal2)  # win_amd64)
PYTHON_VERSIONS=(3.11)
FONTMAKE_VERSION="$(python setup.py --version)"

FONTMAKE_WHEEL="${HERE}/dist/fontmake-${FONTMAKE_VERSION}-py3-none-any.whl"
REQUIREMENTS="${HERE}/requirements.txt"
LICENSE_FILE="${HERE}/LICENSE"

OUTPUT_DIR="${HERE}/shivs"

mkdir -p "${OUTPUT_DIR}"

pushd "${OUTPUT_DIR}"

for platform in ${PLATFORMS[*]}; do
    for version in ${PYTHON_VERSIONS[*]}; do
        v=${version//.}
        abi="cp${v}"
        outdir="fontmake-${FONTMAKE_VERSION}-cp${v}-${abi}-${platform}"
        mkdir -p "${outdir}"

        if [[ $platform == win32 || $platform == win_amd64 ]]; then
            ext=".pyz"
        else
            ext=""
        fi

        shiv -c fontmake \
             -o "${outdir}/fontmake${ext}" \
             -p "/usr/bin/env python${version}" \
             --python-version ${v} \
             --platform ${platform} \
             --abi ${abi} \
             --implementation cp \
             --only-binary=:all: \
             -r "${REQUIREMENTS}" \
             "${FONTMAKE_WHEEL}"

        cp "${HERE}/LICENSE" "${outdir}"
        zip -r "${outdir}.zip" "${outdir}"
        rm -rf "${outdir}"
    done
done

popd
