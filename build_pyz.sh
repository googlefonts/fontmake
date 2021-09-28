#!/bin/bash

set -e
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null && pwd )"

PLATFORMS=(manylinux1_x86_64 macosx_10_6_intel win32 win_amd64)
PYTHON_VERSIONS=(3.7 3.8 3.9)
FONTMAKE_VERSION="$(python setup.py --version)"

FONTMAKE_WHEEL="${HERE}/dist/fontmake-${FONTMAKE_VERSION}-py3-none-any.whl"
REQUIREMENTS="${HERE}/requirements.txt"
LICENSE_FILE="${HERE}/LICENSE"

OUTPUT_DIR="${HERE}/shivs"

mkdir -p "${OUTPUT_DIR}"

pushd "${OUTPUT_DIR}"

for platform in ${PLATFORMS[*]}; do
    for version in ${PYTHON_VERSIONS[*]}; do
        if [ "${version}" == "3.8" ]; then
            if [ "$platform" == "macosx_10_6_intel" ]; then
                # for python 3.8 on macOS we only target >= 10.9 64-bit
                platform="macosx_10_9_x86_64"
            fi
            # python 3.8 removed the 'm' ABI flag
            m=""
        else
            m="m"
        fi
        v=${version//.}
        abi="cp${v}${m}"
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
