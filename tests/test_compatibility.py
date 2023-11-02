import pytest
import ufoLib2
from fontTools import designspaceLib

from fontmake.__main__ import main
from fontmake.compatibility import CompatibilityChecker


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
