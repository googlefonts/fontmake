#/usr/bin/env bash

function check_failure() {
    if [[ $? = 1 ]]; then
        echo $1
        exit 1
    fi
}

fontmake -i -m DesignspaceTest.designspace
check_failure 'Designspace test failed to build'

for src in 'GuidelineTest'; do
    fontmake -i -g "${src}.glyphs"
    check_failure "${src} failed to build"
done
