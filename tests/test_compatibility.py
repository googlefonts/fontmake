import pytest
import ufoLib2
from fontTools import designspaceLib

from fontmake.__main__ import main
from fontmake.compatibility import CompatibilityChecker
from fontmake.errors import FontmakeError


def test_compatibility_checker(data_dir, caplog):
    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        data_dir / "IncompatibleSans" / "IncompatibleSans.designspace"
    )
    designspace.loadSourceFonts(opener=ufoLib2.objects.Font.open)

    CompatibilityChecker([s.font for s in designspace.sources]).check()
    assert "differing number of contours in glyph A" in caplog.text
    assert "Incompatible Sans Regular had: 2" in caplog.text

    assert "differing number of points in glyph B, contour 0" in caplog.text

    assert "differing anchors in glyph A" in caplog.text
    assert 'Incompatible Sans Bold had: "foo"' in caplog.text

    assert "Fonts had differing number of components in glyph C" in caplog.text

    assert (
        "Fonts had differing point type in glyph D, contour 0, point 10" in caplog.text
    )

    assert "differing number of contours in glyph space" in caplog.text
    assert "differing number of contours in glyph E" not in caplog.text


def test_compatibility_cli(data_dir, caplog):
    ds = str(data_dir / "IncompatibleSans" / "IncompatibleSans.designspace")
    with pytest.raises(SystemExit):
        main(["-o", "variable", "-m", ds])

    main(["-o", "ttf", "-m", ds])

    with pytest.raises(SystemExit):
        main(["--check-compatibility", "-o", "ttf", "-m", ds])

    # We stopped things before they got to the cu2qu level
    assert "cu2qu.ufo" not in caplog.text

    with pytest.raises(SystemExit):
        main(["--no-check-compatibility", "-o", "variable", "-m", ds])

    # Things got to the cu2qu level (i.e. compatibility checker did not run)
    assert "cu2qu.ufo" in caplog.text


def test_compatibility_fewer_than_two_sources():
    # a single (or zero) source has nothing to interpolate, so the checker must
    # not blow up indexing a (possibly missing) default source.
    # https://github.com/googlefonts/fontmake/issues/1166
    assert CompatibilityChecker([], default_source_idx=None).check()
    assert CompatibilityChecker([object()], default_source_idx=None).check()


def test_compatibility_no_default_source_raises(data_dir):
    # Two or more interpolatable sources with no default source is a hard error:
    # the checker pre-empts the failure varLib would raise later, rather than
    # silently comparing against an arbitrary source.
    # https://github.com/googlefonts/fontmake/issues/1166
    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        data_dir / "IncompatibleSans" / "IncompatibleSans.designspace"
    )
    designspace.loadSourceFonts(opener=ufoLib2.objects.Font.open)
    fonts = [s.font for s in designspace.sources]
    with pytest.raises(FontmakeError, match="no source found at the default"):
        CompatibilityChecker(fonts, default_source_idx=None).check()


def test_no_default_source_static_build(data_dir, tmp_path):
    # The fixture's only source sits at Weight=700 while the axis default is 400,
    # so DesignSpaceDocument.findDefault() returns None. A static build must not
    # raise "Default source not found!".
    # https://github.com/googlefonts/fontmake/issues/1166
    ds = str(data_dir / "NoDefaultSource" / "NoDefaultSource.designspace")
    main(["-o", "ttf", "-m", ds, "--output-dir", str(tmp_path)])
    assert (tmp_path / "IncompatibleSans-Regular.ttf").exists()

    # an explicit compatibility check on the single source is a no-op, not a crash
    main(
        ["--check-compatibility", "-o", "ttf", "-m", ds, "--output-dir", str(tmp_path)]
    )
