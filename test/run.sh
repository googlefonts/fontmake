#/usr/bin/env bash

fontmake -g 'NotoSansDevanagari/NotoSansDevanagari.glyphs'\
    --mti-source='NotoSansDevanagari/NotoSansDevanagari.plist' -o 'ttf'
for script in 'Ethiopic' 'Hebrew'; do
    fontmake -i -g "NotoSans${script}-MM.glyphs" -o 'ttf'
done
