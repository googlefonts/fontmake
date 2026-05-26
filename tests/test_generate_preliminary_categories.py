"""Unit tests for fontmake.font_project._generate_preliminary_categories.

All tests are in-memory (no disk I/O) and exercise the helper function
directly, covering every early-exit guard and classification path.
"""

import ufoLib2
from fontTools import designspaceLib

from fontmake.font_project import (
    GLYPHS_PREFIX,
    OPENTYPE_CATEGORIES_KEY,
    _generate_preliminary_categories,
)


def make_designspace(font=None):
    """Return a minimal DesignSpaceDocument whose default source has *font*.

    A single source with no location is used so that ``findDefault()``
    returns it unambiguously.
    """
    ds = designspaceLib.DesignSpaceDocument()
    source = designspaceLib.SourceDescriptor()
    source.font = font if font is not None else ufoLib2.Font()
    ds.sources.append(source)
    return ds


class TestEarlyExits:
    def test_returns_none_when_categories_in_designspace_lib(self):
        """Skip generation when the designspace already has explicit categories."""
        ds = make_designspace()
        ds.lib[OPENTYPE_CATEGORIES_KEY] = {"A": "base"}
        assert _generate_preliminary_categories(ds) is None

    def test_returns_none_when_no_sources(self):
        """Skip when there is no default source at all."""
        ds = designspaceLib.DesignSpaceDocument()
        assert _generate_preliminary_categories(ds) is None

    def test_returns_none_when_default_source_has_no_font(self):
        """Skip when the default source exists but its font is not loaded."""
        ds = designspaceLib.DesignSpaceDocument()
        source = designspaceLib.SourceDescriptor()
        # source.font is None by default
        ds.sources.append(source)
        assert _generate_preliminary_categories(ds) is None

    def test_returns_none_when_categories_in_font_lib(self):
        """Skip generation when the default source UFO already has explicit categories."""
        font = ufoLib2.Font()
        font.lib[OPENTYPE_CATEGORIES_KEY] = {"acutecomb": "mark"}
        ds = make_designspace(font)
        assert _generate_preliminary_categories(ds) is None

    def test_returns_none_when_no_classifiable_glyphs(self):
        """Return None (not an empty dict) when no glyphs yield a category."""
        font = ufoLib2.Font()
        # 'space' is Separator/Space — not a mark or ligature
        font.newGlyph("space").unicodes = [0x0020]
        # 'A' is Letter/None — not classified
        font.newGlyph("A").unicodes = [0x0041]
        ds = make_designspace(font)
        assert _generate_preliminary_categories(ds) is None


class TestGlyphDataClassification:
    def test_nonspacing_mark_via_glyphdata(self):
        """Glyphs GlyphData knows as Mark/Nonspacing are classified as 'mark'."""
        font = ufoLib2.Font()
        font.newGlyph("acutecomb").unicodes = [0x0301]
        font.newGlyph("gravecomb").unicodes = [0x0300]
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["acutecomb"] == "mark"
        assert result["gravecomb"] == "mark"

    def test_ligature_via_glyphdata(self):
        """Glyphs GlyphData knows as */Ligature are classified as 'ligature'."""
        font = ufoLib2.Font()
        font.newGlyph("f_i")
        font.newGlyph("f_l")
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["f_i"] == "ligature"
        assert result["f_l"] == "ligature"

    def test_unclassifiable_glyphs_are_absent_from_result(self):
        """Glyphs that are neither mark nor ligature must not appear in the result."""
        font = ufoLib2.Font()
        font.newGlyph("acutecomb").unicodes = [0x0301]  # mark
        font.newGlyph("A").unicodes = [0x0041]  # letter — not classified
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert "A" not in result

    def test_marks_and_ligatures_coexist(self):
        """Both marks and ligatures can appear together in one result dict."""
        font = ufoLib2.Font()
        font.newGlyph("acutecomb").unicodes = [0x0301]
        font.newGlyph("f_i")
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["acutecomb"] == "mark"
        assert result["f_i"] == "ligature"


class TestPerGlyphLibOverrides:
    def test_mark_via_lib_override(self):
        """A glyph classified as mark via its lib keys is returned as 'mark'."""
        font = ufoLib2.Font()
        g = font.newGlyph("customMark")
        g.lib[GLYPHS_PREFIX + "Glyphs.category"] = "Mark"
        g.lib[GLYPHS_PREFIX + "Glyphs.subCategory"] = "Nonspacing"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["customMark"] == "mark"

    def test_spacing_combining_mark_via_lib_override(self):
        """Mark/Spacing Combining in the lib keys is classified as 'mark'."""
        font = ufoLib2.Font()
        g = font.newGlyph("spacingMark")
        g.lib[GLYPHS_PREFIX + "Glyphs.category"] = "Mark"
        g.lib[GLYPHS_PREFIX + "Glyphs.subCategory"] = "Spacing Combining"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["spacingMark"] == "mark"

    def test_ligature_via_lib_override(self):
        """A glyph with subCategory=Ligature in its lib keys is classified as 'ligature'."""
        font = ufoLib2.Font()
        g = font.newGlyph("customLigature")
        g.lib[GLYPHS_PREFIX + "Glyphs.subCategory"] = "Ligature"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["customLigature"] == "ligature"

    def test_lib_override_beats_glyphdata_for_mark(self):
        """Per-glyph lib keys take precedence over GlyphData when classifying marks."""
        font = ufoLib2.Font()
        # acutecomb is Mark/Nonspacing in GlyphData, but lib says it's a Letter
        g = font.newGlyph("acutecomb")
        g.unicodes = [0x0301]
        g.lib[GLYPHS_PREFIX + "Glyphs.category"] = "Letter"
        g.lib[GLYPHS_PREFIX + "Glyphs.subCategory"] = "Uppercase"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        # lib override removes acutecomb from any classifiable category, so nothing remains
        assert result is None

    def test_lib_override_beats_glyphdata_for_ligature(self):
        """Per-glyph lib keys take precedence over GlyphData when classifying ligatures."""
        font = ufoLib2.Font()
        # f_i is Letter/Ligature in GlyphData, but lib says it's a plain Letter
        g = font.newGlyph("f_i")
        g.lib[GLYPHS_PREFIX + "Glyphs.category"] = "Letter"
        g.lib[GLYPHS_PREFIX + "Glyphs.subCategory"] = "Uppercase"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        # lib override removes f_i from any classifiable category, so nothing remains
        assert result is None

    def test_partial_lib_override_falls_back_to_glyphdata(self):
        """When only the category lib key is set, subCategory falls back to GlyphData."""
        font = ufoLib2.Font()
        # f_i is Letter/Ligature in GlyphData; override category to something else
        # but leave subCategory unset so it falls through to GlyphData's "Ligature"
        g = font.newGlyph("f_i")
        g.lib[GLYPHS_PREFIX + "Glyphs.category"] = "Letter"  # same as GlyphData
        # subCategory not set → GlyphData supplies "Ligature"
        ds = make_designspace(font)
        result = _generate_preliminary_categories(ds)
        assert result is not None
        assert result["f_i"] == "ligature"


class TestLogging:
    def test_info_logged_when_categories_generated(self, caplog):
        """An INFO message must be emitted when preliminary categories are generated."""
        import logging

        font = ufoLib2.Font()
        font.newGlyph("acutecomb").unicodes = [0x0301]
        ds = make_designspace(font)
        with caplog.at_level(logging.INFO, logger="fontmake.font_project"):
            _generate_preliminary_categories(ds)
        assert any(
            "preliminary openTypeCategories" in r.message for r in caplog.records
        )

    def test_no_log_when_returning_none(self, caplog):
        """No INFO message must be emitted when the function returns None early."""
        import logging

        ds = make_designspace()
        ds.lib[OPENTYPE_CATEGORIES_KEY] = {"A": "base"}
        with caplog.at_level(logging.INFO, logger="fontmake.font_project"):
            _generate_preliminary_categories(ds)
        assert not any(
            "preliminary openTypeCategories" in r.message for r in caplog.records
        )
