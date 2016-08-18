#/usr/bin/env bash

function check_failure() {
    if [[ $? = 1 ]]; then
        echo $1
        exit 1
    fi
}

for src in 'GuidelineTest' 'NotoSansEthiopic-MM' 'NotoSansHebrew-MM'; do
    fontmake -i -g "${src}.glyphs"
    check_failure "${src} failed to build"
done
fontmake -g 'NotoSansDevanagari/NotoSansDevanagari.glyphs'\
    --mti-source='NotoSansDevanagari/NotoSansDevanagari.plist'
check_failure 'Devanagari failed to build'

echo "running $(./fontdiff --version)"
for script in 'Ethiopic' 'Hebrew'; do
    family="NotoSans${script}"
    ./fontdiff --before "expected/${family}-Regular.otf"\
        --after "instance_otf/${family}-Regular.otf"\
        --specimen "${family}.html"\
        --out "${family}.pdf"
    check_failure "differences found in ${family} output"
done
