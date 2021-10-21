# Advanced Usage

This guide assumes that you have read the basic instructions in `README.md`.

## Functional overview

`fontmake` has many more options than the basic ones outlined in `README.md`.
These options customize various elements of the font compilation process, and so
to understand the options, it helps to understand the general outline of the
process by which `fontmake` creates binary fonts.

Here are the basic operations:

* Convert Glyphs file to `.designspace` and `.ufo` files.
* Run pre-processing filters. (Convert cubics to quadratics for TTF outlines, decompose mixed glyphs, remove overlaps, etc.)
* Generate explicit feature files. (Turn anchor and kerning information in source file into Adobe feature file syntax, so that it can be compiled into OpenType layout.)
* Create outlines.
* Build OpenType tables.
* Run post-processing filters. (Rename glyphs to production names.)

For most people, the default settings will produce optimal results, but in some situations you may wish to alter the default operation.

## General options

* `--no-production-names`: By default, `fontmake` renames the glyphs in the output binary font file during post-processing based on the value of the `public.postscriptNames` lib key in the UFO file. (In the case of Glyphs source files, conversion to UFO populates this lib key with the production names from the Glyphs file.) Any encoded glyphs without production names are renamed to `uniXXXX` based on their Unicode code point, unencoded ligature glyphs are renamed based on the production names of their components, and other unencoded glyphs are not renamed. The `--no-production-names` flag suppresses all glyph renaming.

* `-a`/`-a "<arguments>"`: Run ttfautohint on TrueType output binary font files. If any arguments are provided in a quoted string, these are passed to the `ttfautohint` binary.

* `--mti-source <plist>`: Instead of generating feature files from the design sources, this takes an external plist file which links masters to Monotype FontDame feature definition files. You may safely ignore this option unless you are compiling Monotype-supplied font sources for the Noto project.

## Options for Glyphs sources

* `--no-write-skipexportglyphs`: When converting the Glyphs sources to UFO, all glyphs, even glyphs not set to be exported into the font, are converted to UFO format. Glyphs which are set as unexported are listed in the `public.skipExportGlyphs` lib key of the UFO and designspace files. Before this key was standardized by UFO, older versions of `fontmake` would use a private lib key, `com.schriftgestaltung.Glyphs.Export` instead. If you are managing a workflow which tracks files created by an older version of `fontmake`, you may wish to use this flag to use the older lib key and maintain compatibility with those files.

* `--instance-dir <path>`: When generating static instances from Glyphs sources with the `-i` flag, `fontmake` writes UFO files representing the instances to the `instance_ufo` directory by default before compiling them to binary. This flag directs `fontmake` to write these temporary UFO files to another directory. If you pass the special value `{tmp}`, `fontmake` uses a temporary directory which it removes after processing.

* `--master-dir <path>`: Similarly, this specifies the directory to be used when writing UFO files representing the font masters.

* `--designspace-path <path>`: When converting the masters to UFO, `fontmake` also creates a Designspace file in the `master_ufo` directory. This option specifies the path where the Designspace file should be written.

* `--family-name <family name>`: When this flag is provided, the masters are given the family name supplied, and only instances containing that family name are exported. For example, you can use this to create multiple optical-size-specific subfamilies from a single Glyphs file; `--family-name "MyFont 12pt"` will set the family name to `MyFont 12pt` and only export the instances which contain `MyFont 12pt` in the `familyName` custom parameter of the instance definition.

* `--subset` / `--no-subset`: By default, `fontmake` determines whether or not to subset an instance based on the presence or absence of "Keep Glyphs" custom parameter on the instance. To turn off subsetting despite the presence of a "Keep Glyphs" custom parameter, use the `--no-subset` flag.

## Options for TrueType outlines

* `--keep-overlaps`: By default, `fontmake` performs overlap removal on TrueType outlines, except when producing interpolatable or variable fonts. This flag directs `fontmake` to skip the overlap removal preprocessing step.

* `--overlaps-backend booleanOperations|pathops`: Chooses the library for overlap removal. Skia's pathops library is faster but requires an additional library to be installed, and also appears to [fail on some glyphs](https://github.com/google/fonts/issues/3365), hence the default is the `booleanOperations` library.

* `--no-optimize-gvar`: When compiling a variable font, the variation information is stored in a table called the `gvar` table inside the binary. OpenType allows fonts to omit some variations in the outlines if the variation information can be inferred from the surrounding points - for example, points along a line will often change at a rate determined by the average of the variations of their neighbours. Omitting variations for such points makes the font size smaller, so `fontmake` performs this optimization by default: this is called "Interpolation of Untouched Points", or IUP. This flag turns off the IUP optimization.

* `--keep-direction`: Generally speaking, filled outlines in a TrueType font should have their points arranged in clockwise order and counter outlines should have their points in anti-clockwise order; design tools tend to order contours the other way around, so `fontmake` reverses the outlines when generating TrueType fonts. This flag keeps the outline direction as specified in the font source.

* `--conversion-error ERROR`: When TrueType outlines are converted to binary, the curves are converted from cubic Béziers in the design sources to quadratic Bézier splines. However, as this conversion involves a degree reduction, it is not completely accurate, and hence the quadratic curves approximate the cubic originals. This flag controls the maximum permissible error, measured in ems. the default is 0.001, or one unit at 1000upm. Larger values will result in smaller font sizes, particularly for CJK fonts, but at the cost of fidelity to the original curves.

* `--no-generate-GDEF`: As part of generating explicit feature files, `fontmake` uses the glyph categories in the source file to create a `table GDEF { ... } GDEF;` statement in the generated feature file; this is then compiled into the `GDEF` table of the font binaries. However, if the feature file in your source *also* contains a `table GDEF` statement, the font will fail to compile. In this case, you can add the `--no-generate-GDEF` flag to turn off writing an additional `table GDEF` statement in the generated feature file.

## Options for CFF outlines

* `--cff-round-tolerance FLOAT`: Controls the way that point coordinates are rounded in the CFF table. The default value of 0.5 rounds points to the nearest integer. Setting this value to 0 disables all coordinate rouding.

* `--optimize-cff VALUE`: By default, the CFF table is compressed in two ways: in *specialization*, drawing operations are chosen which most efficiently express the contour. For example, where there is a horizontal line, it is more efficient to use the specialized `hlineto` drawing operator instead of the more general `lineto` operator, as the `lineto` operator takes two parameters (`dx dy`) and `dy` will always be zero in the case of horizontal lines, whereas `hlineto` only takes a `dx` parameter.

Additionally, there is *subroutinization*, which places common sequences of operations into subroutines; this is somewhat similar to components, but at a lower level - for example, a stem with a serif which occurs in multiple glyphs might be subroutinized.

This flag controls the degree of compression: 0 disables all optimizations; 1 applies specialization but disables subroutinization; and 2, the default, applies both specialization and subroutinization. You may want this flag if you are debugging CFF tables and want to compare the drawing operators more directly against the source outlines.

* `--subroutinizer compreffor|cffsubr`: The work of CFF subroutinization, as described above, is one of the many things in `fontmake` that are outsourced to a separate Python library. The two libraries used are `compreffor` (the default for CFF1 - indeed, it only supports CFF1) and `cffsubr` (the default for CFF2). If you want to see whether `cffsubr` compresses the font better, you can use this flag to change the library used for subroutinization.

## Options for instance generation

* `-i <instance name>`: `-i` was introduced in the Basic Usage section for interpolating masters and generating instances. The flag may also be followed by an argument which is a string or regular expression; if this is provided, then only those instances which match the string will be generated. For example,`-i "Noto Sans Bold"`; `-i ".* UI Condensed"`.

* `--use-mutatormath`: When generating instances from a designspace file, there are (again) two possible Python libraries which perform the interpolation: fontmake's internal `instantiator` module, and `mutatormath`. `instantiator` is a deliberately minimal implementation which works in most cases, but it does not support extrapolation (instances whose coordinates are placed outside of the range of the masters) or anisotropic locations (axes which have different degrees of variation on the X axis to the Y axis; these are not possible in OpenType variable fonts, but can be used to generate static instances in Fontlab VI and some Robofont extensions).

* `-M`, `--masters-as-instances`: This flag causes `fontmake` to also create instance binaries for each master defined in the font, even if they are not explicitly exported as instances by default.

* `--round-instances`: This option rounds glyph outlines when generating instances. (XXX Surely they're rounded to ints when they're written to the `glyf` table anyway. What does this actually do?)

* `--expand-features-to-instances`: If any feature files within the design sources contain `include()` statements, and these statements contain a relative path, instances may fail to build because they are being compiled in a different directory to the original where the included feature files cannot be found. In that case, you should use this flag to expand all the `include()` statements before the instance is compiled. We know that you shouldn't have to do this by hand, and we will make it the default one day.

* `--interpolate-binary-layout <directory>`: When `fontmake` generates instances, it creates a feature file for each master using feature writers, but it also creates an *interpolated* feature file using feature writers for static instances. But while feature writers can interpolate kerning and anchor positions, they do *not* interpolate explicit `pos` statements given in the source feature files - nor do they interpolate layout rules expressed in MonoType FontDame format. (See the `--mti-source` option.) In order to perform this interpolation, `fontmake` needs to build the binary master files and interpolate the GPOS tables directly, rather than the textual representation of layout rules. Hence, if you have explicit `pos` statements in the feature files of your masters and you need these to interpolate in instances, use this flag.

## Outline Filtering

As mentioned in the functional overview, `fontmake` has two "filtering" passes, a "preprocessing" pass on the UFO files which converts cubics to quadratics for TTF glyphs, removes overlaps, and so on, and a "postprocessing" pass on the output binary files. It is possible to add your own filters into this pipeline to further customize the font building process, and to achieve custom effects similar to Glyphs export filters.

This can be done in two ways: either by writing, manually or automatically, entries into a `lib` key (`com.github.googlei18n.ufo2ft.filters`) in the `.designspace` or UFO file, or on the command line. For example, when converting from Glyphs to UFO, `fontmake` (via the `glyphsLib` library) adds the following entry to the UFO `lib.plist`:

```xml
    <key>com.github.googlei18n.ufo2ft.filters</key>
    <array>
      <dict>
        <key>name</key>
        <string>eraseOpenCorners</string>
        <key>namespace</key>
        <string>glyphsLib.filters</string>
        <key>pre</key>
        <true/>
      </dict>
    </array>
```

This calls the `EraseOpenCornersFilter` class from the Python module `glyphsLib.filters.eraseOpenCorners` as part of the `pre`-processing step, which converts any external open corners in the glyph outlines into plain corners.

Any Python class inheriting from [`ufo2ft.filters.BaseFilter`](https://github.com/googlefonts/ufo2ft/blob/main/Lib/ufo2ft/filters/base.py) can be used as a filter, although the `namespace` must be provided, as in this case. Filters available through the `ufo2ft` library do not require a `namespace` key, as this library is the default source of filters. Filters can be further customized through optional arguments, as described below.

To apply filters via a command-line, use the `--filter` argument with the following syntax: `--filter "python.package::ClassName(argument,argument)`; add the pseudo-argument `pre=True` to run the filter as a preprocessing step. For example, to use the `ufostroker` library to apply "noodling" effects to open paths in a source font, use `--filter 'ufostroker::StrokeFilter(Width=50,pre=True)`.

### Included filters

The `ufo2ft` library provides some default filters described below. Most of the filters are called automatically as part of `fontmake`'s ordinary pipeline, but some can be added manually. The filters are run in the following order:

* (Any manually added pre-filters are called first.)

* `ExplodeColorLayerGlyphs`: Called automatically to create glyphs out of color layers when constructing a `COLR` font with `colorPalettes` and `colorLayerMapping` lib keys.

* `DecomposeComponents`: Called automatically when producing OTF outlines, and called on glyphs which have components *and* outlines when producing TTF binaries.

* `FlattenComponents`: Called automatically to flatten nested components when the `-f` flag is passed to `fontmake`.

* `RemoveOverlaps`: Called automatically to remove overlaps.

* `CubicToQuadratic`: Called automatically when producing TTF binaries.

* (Any manually added post-filters are called last.)

Other filters available as part of `ufo2ft` are:

* `DecomposeTransformedComponents`: Decomposes any components which have a non-identity transformation matrix (i.e. which are translated or scaled). For example, a `u` glyph from an `n` component flipped horizontally. Fonts constructed in this way can have rasterizing and hinting errors (see [here](https://github.com/googlefonts/fontmake/issues/253) and [here](https://github.com/googlefonts/fontbakery/issues/2011)). To fix fonts with these errors, add `--filter DecomposeTransformedComponentsFilter` to the `fontmake` command line.

* `PropagateAnchors`: Creates additional anchors for composite glyphs based on the anchors of their components.

* `SortContours`: Sorts the contours based on their bounding box size. Can be added manually to alleviate overlap removal bugs, but must be manually placed in the UFO lib so that it is executed between `DecomposeComponents` and `RemoveOverlaps`.

* `Transformations`: Similar to the Glyphs "Transformations" filter, this allows for outlines to be scaled, translated or transformed on export. For example, to scale down and raise up the glyphs "A" and "B" of a font, add this to the lib file:

```xml
    <key>com.github.googlei18n.ufo2ft.filters</key>
    <array>
      <dict>
        <key>name</key>
        <string>transformations</string>
        <key>kwargs</key>
        <dict>
            <key>OffsetX</key>
            <integer>0</integer>
            <key>OffsetY</key>
            <integer>150</integer>
            <key>ScaleX</key>
            <integer>75</integer>
            <key>ScaleY</key>
            <integer>75</integer>
        </dict>
        <key>include</key>
        <array>
            <string>A</string>
            <string>B</string>
        </array>
      </dict>
    </array>
```

## Feature writing

In a similar vein to the filter classes, `fontmake` allows you to customize the way that kerning and anchor rules in the font sources are turned into explicit rules in the autogenerated feature file. These generated rules are written by classes called feature writers. The feature writers can also be customized with a lib key, `com.github.googlei18n.ufo2ft.featureWriters`.

For example, all feature writers take the `mode` option, which takes either the value `append` or `skip`. The default is `skip`, which will skip writing the feature if the feature is already explicitly present in the design sources' features file.

> However, note that even in `skip` mode, if the existing feature code contains the magic string `# Automatic Code`, the feature code generated by fontmake will be inserted into the feature file at the location of the comment.

To change this to `append` for the kern feature writer (i.e. to add generated kerning rules from the kerning table onto the end of the manually supplied `kern` feature), you would add the following lib key:

```xml
    <key>com.github.googlei18n.ufo2ft.featureWriters</key>
    <array>
        <dict>
            <key>class</key>
            <string>KernFeatureWriter</string>
            <key>options</key>
            <dict>
                <key>mode</key>
                <string>append</string>
            </dict>
        </dict>
    </array>
```

There is also a `--feature-writer` option, analogous to `--filters`, allowing you to load custom feature writers on the command line. The special value `--feature-writer "None"` disables all automatic feature generation.

`ufo2ft` provides three feature writer classes:

* `GdefFeatureWriter` generates the `table GDEF { } GDEF;` statement, based on the categories of the glyphs (stored in the `public.openTypeCategories` lib key of the source font) and ligature caret anchors (anchors starting with `caret_` or `vcaret_`). It has no customizable parameters. It can be disabled with the `--no-generate-GDEF` flag.

* `KernFeatureWriter` generates kerning features (or, for certain complex scripts, `dist` features) based on the kerning information in the design sources. It has two optional parameters in addition to `mode`: `ignoreMarks`, which defaults to `True`, will emit an `LookupFlag IgnoreMarks` in the generated `kern` feature; setting this to `False` will generate kern rules which do not ignore mark glyphs. Additionally, `quantization` can be set to an integer value to round the kern rules to the nearest multiple of its value, which can help with compressing the tables.

* `MarkFeatureWriter` generates `mark` and `mkmk` features based on the anchor information in the design sources. It has one optional parameter, `quantization`, which rounds the anchor positions to the nearest multiple of its value, which makes anchors more likely to be shared in the `GPOS` table, potentially reducing its size at the expense of some fidelity.
