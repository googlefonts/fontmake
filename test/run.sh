#/usr/bin/env bash

fontmake -g 'NotoSansDevanagari/NotoSansDevanagari.glyphs'\
    --mti-source='NotoSansDevanagari/NotoSansDevanagari.plist'
for script in 'Ethiopic' 'Hebrew'; do
    fontmake -i -g "NotoSans${script}-MM.glyphs"
done

for script in 'Ethiopic' 'Hebrew'; do
    family="NotoSans${script}"
    ./fontdiff-linux --before "expected/${family}-Regular.otf"\
        --after "instance_otf/${family}-Regular.otf"\
        --specimen "${family}.html"\
        --out "${family}.pdf"
    if [[ $? = 1 ]]; then
        echo "differences found in ${family} output"
        exit 1
    fi
done
