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
    echo "# Testing ${src} with interpolation"
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -i -m "${src}.designspace"
    check_failure "${src} failed to build"
    cd ..
done

for src in 'DesignspaceTest' 'AvarDesignspaceTest'; do
    echo "# Testing ${src} with interpolation and masters-as-instances"
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -i -M -m "${src}.designspace"
    check_failure "${src} failed to build"
    cd ..
done

for src in 'DesignspaceTestSharedFeatures'; do
    echo "# Testing ${src} with interpolation and master feature expansion"
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -i --expand-features-to-instances -m "${src}.designspace" -o ttf
    check_failure "${src} failed to build"
    grep -Fxq "# test" "instance_ufo/DesignspaceTest-Light.ufo/features.fea"
    check_failure "${src} failed to build: no feature file in instance UFO"
    cd ..
done

for src in 'DesignspaceTestSharedFeatures'; do
    echo "# Testing ${src} without interpolation"
    cd "${src}"
    mkdir -p instance_ufo
    fontmake -u "DesignspaceTest-Light.ufo" -o ttf
    check_failure "${src} failed to build"
    cd ..
done

for src in 'InterpolateLayoutTest'; do
    echo "# Testing ${src}"
    cd "${src}"
    fontmake -g "${src}.glyphs" --mti-source "${src}.plist" --no-production-names
    fontmake -g "${src}.glyphs" -i --interpolate-binary-layout --no-production-names
    check_failure "${src} failed to build"
    cd ..
done

for src in 'GuidelineTest'; do
    echo "# Testing ${src}"
    fontmake -i -g "${src}.glyphs"
    check_failure "${src} failed to build"
done

for src in 'GlyphsUnitTestSans'; do
    echo "# Testing ${src} with -i -o ufo"
    fontmake -i -g "${src}.glyphs" -o ufo
    check_failure "${src} failed to build"
    if [ ! "$(ls -A instance_ufo)" ]; then
        echo "error: instance_ufo dir is empty"
        exit 1
    fi
done

echo "# Testing subsetting with TestSubset.glyphs"
fontmake -g TestSubset.glyphs -i "Test Subset Regular" -o ttf otf
check_failure "TestSubset.glyphs failed to build"

echo "# Running test_output.py"
python test_output.py
check_failure 'fontmake output incorrect'

echo "# Running test_arguments.py"
python test_arguments.py
check_failure 'fontmake output incorrect'
