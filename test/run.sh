#/usr/bin/env bash

function check_failure() {
    if [[ $? = 1 ]]; then
        echo $1
        exit 1
    fi
}

fontmake -g 'NotoSansDevanagari/NotoSansDevanagari.glyphs'\
    --mti-source='NotoSansDevanagari/NotoSansDevanagari.plist'
check_failure 'Devanagari failed to build'
for script in 'Ethiopic' 'Hebrew'; do
    fontmake -i -g "NotoSans${script}-MM.glyphs"
    check_failure "${script} failed to build"
done

echo "running $(fontdiff --version)"
for script in 'Ethiopic' 'Hebrew'; do
    family="NotoSans${script}"
    ./fontdiff --before "expected/${family}-Regular.otf"\
        --after "instance_otf/${family}-Regular.otf"\
        --specimen "${family}.html"\
        --out "${family}.pdf"
    check_failure "differences found in ${family} output"
done
