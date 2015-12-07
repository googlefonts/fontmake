# fontmake

This library provides a wrapper for several other Python libraries which
together compile fonts from various sources (.glyphs, .ufo) into binaries (.otf,
.ttf).

### Install

```bash
sudo python setup.py develop
```

### Run

After installation, fontmake can be run end-to-end as a module:

```bash
# outputs master binaries
python -m fontmake MyFont.glyphs
```

Use `-h` to see a list of runtime options. `-i` will output instance binaries,
`-c` will ensure the output is interpolation compatible (for both masters and
instances).

You can also use fontmake to run intermediate steps in the build process, via
methods of the `fontmake.font_project.FontProject` class.
