#/usr/bin/env bash
#
# Copyright 2016 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


function check_failure() {
    if [[ $? = 1 ]]; then
        echo $1
        exit 1
    fi
}

for src in 'DesignspaceTest' 'AvarDesignspaceTest'; do
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -i -m "${src}.designspace"
    check_failure "${src} failed to build"
    cd ..
done

# also test the masters_as_instance parameter
for src in 'DesignspaceTest' 'AvarDesignspaceTest'; do
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -i -M -m "${src}.designspace"
    check_failure "${src} failed to build"
    cd ..
done

for src in 'InterpolateLayoutTest'; do
    cd "${src}"
    fontmake -g "${src}.glyphs" --mti-source "${src}.plist" --no-production-names
    fontmake -g "${src}.glyphs" -i --interpolate-binary-layout --no-production-names
    check_failure "${src} failed to build"
    cd ..
done

for src in 'GuidelineTest'; do
    fontmake -i -g "${src}.glyphs"
    check_failure "${src} failed to build"
done

fontmake -g TestSubset.glyphs -i "Test Subset Regular" -o ttf otf
check_failure "TestSubset.glyphs failed to build"

python test_output.py
check_failure 'fontmake output incorrect'

python test_arguments.py
check_failure 'fontmake output incorrect'
