import ufoLib2
from fontTools import designspaceLib

from fontmake.compatibility import CompatibilityChecker


def test_compatibility_checker(data_dir, caplog):
    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        data_dir / "IncompatibleSans" / "IncompatibleSans.designspace"
    )
    designspace.loadSourceFonts(opener=ufoLib2.objects.Font.open)

    CompatibilityChecker([s.font for s in designspace.sources]).check()
    assert "differing number of contours in glyph A" in caplog.text
    assert "Incompatible Sans Regular had 2" in caplog.text

    assert "differing number of points in glyph B, contour 0" in caplog.text

    assert "differing anchors in glyph A" in caplog.text
    assert 'Incompatible Sans Bold had "foo"' in caplog.text

    assert "Fonts had differing number of components in glyph C" in caplog.text

    assert (
        "Fonts had differing point type in glyph D, contour 0, point 10" in caplog.text
    )
