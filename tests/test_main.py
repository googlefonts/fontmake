import shutil

import fontTools.designspaceLib as designspaceLib
import fontTools.ttLib
import pytest
import ufoLib2

import fontmake.__main__


def test_interpolation(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-i",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Regular.ttf",
        "MyFont-Regular.otf",
    }

    test_output_ttf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.ttf")
    assert test_output_ttf["OS/2"].usWeightClass == 400
    glyph = test_output_ttf.getGlyphSet()["l"]._glyph
    assert glyph.xMin == 50
    assert glyph.xMax == 170

    test_output_otf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.otf")
    assert test_output_otf["OS/2"].usWeightClass == 400
    glyph_set = test_output_otf.getGlyphSet()
    glyph = glyph_set["l"]._glyph
    x_min, _, x_max, _ = glyph.calcBounds(glyph_set)
    assert x_min == 50
    assert x_max == 170


def test_interpolation_mutatormath(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-i",
            "--use-mutatormath",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Regular.ttf",
        "MyFont-Regular.otf",
    }

    test_output_ttf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.ttf")
    assert test_output_ttf["OS/2"].usWeightClass == 400
    glyph = test_output_ttf.getGlyphSet()["l"]._glyph
    assert glyph.xMin == 50
    assert glyph.xMax == 170

    test_output_otf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.otf")
    assert test_output_otf["OS/2"].usWeightClass == 400
    glyph_set = test_output_otf.getGlyphSet()
    glyph = glyph_set["l"]._glyph
    x_min, _, x_max, _ = glyph.calcBounds(glyph_set)
    assert x_min == 50
    assert x_max == 170


def test_interpolation_mutatormath_source_layer(data_dir, tmp_path):
    shutil.copytree(data_dir / "MutatorSans", tmp_path / "layertest")

    with pytest.raises(SystemExit, match="sources with 'layer'"):
        fontmake.__main__.main(
            [
                "-m",
                str(tmp_path / "layertest" / "MutatorSans.designspace"),
                "-i",
                "--use-mutatormath",
                "--output-dir",
                str(tmp_path),
            ]
        )


def test_interpolation_and_masters_as_instances(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-i",
            "-M",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Bold.otf",
        "MyFont-Bold.ttf",
        "MyFont-Light.otf",
        "MyFont-Light.ttf",
        "MyFont-Regular.otf",
        "MyFont-Regular.ttf",
    }

    test_output_ttf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.ttf")
    assert test_output_ttf["OS/2"].usWeightClass == 400
    glyph = test_output_ttf.getGlyphSet()["l"]._glyph
    assert glyph.xMin == 50
    assert glyph.xMax == 170

    test_output_otf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.otf")
    assert test_output_otf["OS/2"].usWeightClass == 400
    glyph_set = test_output_otf.getGlyphSet()
    glyph = glyph_set["l"]._glyph
    x_min, _, x_max, _ = glyph.calcBounds(glyph_set)
    assert x_min == 50
    assert x_max == 170


def test_masters_and_instances_ttf_interpolatable(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-o",
            "ttf-interpolatable",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Bold.ttf",
        "MyFont-Light.ttf",
        "DesignspaceTest.designspace",
    }

    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        tmp_path / "DesignspaceTest.designspace"
    )
    assert {s.filename for s in designspace.sources} == {
        "MyFont-Bold.ttf",
        "MyFont-Light.ttf",
    }


def test_masters_and_instances_otf_interpolatable(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-o",
            "otf-interpolatable",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Bold.otf",
        "MyFont-Light.otf",
        "DesignspaceTest.designspace",
    }

    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        tmp_path / "DesignspaceTest.designspace"
    )
    assert {s.filename for s in designspace.sources} == {
        "MyFont-Bold.otf",
        "MyFont-Light.otf",
    }


def test_variable_ttf(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-o",
            "variable",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {"DesignspaceTest-VF.ttf"}


def test_variable_otf(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "-o",
            "variable-cff2",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {"DesignspaceTest-VF.otf"}


def test_no_interpolation(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTest.designspace"),
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MyFont-Bold.otf",
        "MyFont-Bold.ttf",
        "MyFont-Light.otf",
        "MyFont-Light.ttf",
    }


def test_ufo_interpolation(data_dir, tmp_path):
    shutil.copyfile(
        data_dir / "GlyphsUnitTestSans.glyphs", tmp_path / "GlyphsUnitTestSans.glyphs"
    )

    instance_dir = tmp_path / "instance_ufos"
    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "GlyphsUnitTestSans.glyphs"),
            "--master-dir",
            str(tmp_path / "master_ufos"),
            "--instance-dir",
            str(instance_dir),
            "-i",
            "-o",
            "ufo",
        ]
    )

    assert {p.name for p in instance_dir.glob("*.ufo")} == {
        "GlyphsUnitTestSans-Black.ufo",
        "GlyphsUnitTestSans-Bold.ufo",
        "GlyphsUnitTestSans-ExtraLight.ufo",
        "GlyphsUnitTestSans-Light.ufo",
        "GlyphsUnitTestSans-Medium.ufo",
        "GlyphsUnitTestSans-Regular.ufo",
        "GlyphsUnitTestSans-Thin.ufo",
        "GlyphsUnitTestSans-Web.ufo",
    }


def test_ufo_interpolation_specific(data_dir, tmp_path):
    shutil.copyfile(
        data_dir / "GlyphsUnitTestSans.glyphs", tmp_path / "GlyphsUnitTestSans.glyphs"
    )

    instance_dir = tmp_path / "instance_ufos"
    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "GlyphsUnitTestSans.glyphs"),
            "--master-dir",
            str(tmp_path / "master_ufos"),
            "--instance-dir",
            str(instance_dir),
            "-i",
            r".*Light.*",
            "-o",
            "ufo",
        ]
    )

    assert {p.name for p in instance_dir.glob("*.ufo")} == {
        "GlyphsUnitTestSans-ExtraLight.ufo",
        "GlyphsUnitTestSans-Light.ufo",
    }


@pytest.mark.parametrize(
    "write_skipexportglyphs",
    [
        pytest.param(True, id="default"),
        pytest.param(False, id="no-write-skipexportglyphs"),
    ],
)
def test_subsetting(data_dir, tmp_path, write_skipexportglyphs):
    shutil.copyfile(data_dir / "TestSubset.glyphs", tmp_path / "TestSubset.glyphs")

    args = [
        "-g",
        str(tmp_path / "TestSubset.glyphs"),
        "--master-dir",
        str(tmp_path / "master_ufos"),
        "--instance-dir",
        str(tmp_path / "instance_ufos"),
        "-i",
        "Test Subset Regular",
        "-o",
        "ttf",
        "otf",
        "--output-dir",
        str(tmp_path),
    ]
    if not write_skipexportglyphs:
        args.append("--no-write-skipexportglyphs")

    fontmake.__main__.main(args)

    for output_format in ("ttf", "otf"):
        for font_path in tmp_path.glob("*." + output_format):
            font = fontTools.ttLib.TTFont(font_path)
            assert font.getGlyphOrder() == [".notdef", "space", "A", "C"]


def test_shared_features_expansion(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTestSharedFeatures", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTestSharedFeatures.designspace"),
            "-i",
            "--expand-features-to-instances",
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path),
        ]
    )

    test_feature_file = (
        tmp_path / "sources/instance_ufo/DesignspaceTest-Light.ufo/features.fea"
    )
    assert test_feature_file.read_text() == "# test"


def test_shared_features_ufo(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTestSharedFeatures", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-u",
            str(tmp_path / "sources" / "DesignspaceTest-Light.ufo"),
            str(tmp_path / "sources" / "DesignspaceTest-Regular.ufo"),
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "DesignspaceTest-Light.ttf",
        "DesignspaceTest-Regular.ttf",
    }


def test_mti_sources(data_dir, tmp_path):
    shutil.copytree(data_dir / "InterpolateLayoutTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "sources" / "InterpolateLayoutTest.glyphs"),
            "--designspace-path",
            str(tmp_path / "InterpolateLayoutTest.designspace"),
            "--master-dir",
            str(tmp_path / "master_ufos"),
            "--instance-dir",
            str(tmp_path / "instance_ufos"),
            "--mti-source",
            str(tmp_path / "sources" / "InterpolateLayoutTest.plist"),
            "--no-production-names",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "InterpolateLayoutTest-Bold.otf",
        "InterpolateLayoutTest-Bold.ttf",
        "InterpolateLayoutTest-Light.otf",
        "InterpolateLayoutTest-Light.ttf",
        "InterpolateLayoutTest.designspace",
    }

    font_bold = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Bold.ttf")
    assert font_bold["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font_bold["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -40
    )

    font_light = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Light.ttf")
    assert font_light["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font_light["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -12
    )


def test_interpolate_layout(data_dir, tmp_path):
    shutil.copytree(data_dir / "InterpolateLayoutTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "sources" / "InterpolateLayoutTest.glyphs"),
            "--designspace-path",
            str(tmp_path / "InterpolateLayoutTest.designspace"),
            "--master-dir",
            str(tmp_path / "master_ufos"),
            "--instance-dir",
            str(tmp_path / "instance_ufos"),
            "--mti-source",
            str(tmp_path / "sources" / "InterpolateLayoutTest.plist"),
            "--no-production-names",
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path / "master_ttf"),
        ]
    )

    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "sources" / "InterpolateLayoutTest.glyphs"),
            "--designspace-path",
            str(tmp_path / "InterpolateLayoutTest.designspace"),
            "--master-dir",
            str(tmp_path / "master_ufos"),
            "--instance-dir",
            str(tmp_path / "instance_ufos"),
            "-i",
            "--interpolate-binary-layout",
            str(tmp_path / "master_ttf"),
            "--no-production-names",
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path),
        ]
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Black.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -40
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Bold.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -35
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-SemiBold.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -29
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Regular.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -22
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-Light.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -15
    )

    font = fontTools.ttLib.TTFont(tmp_path / "InterpolateLayoutTest-ExtraLight.ttf")
    assert font["GDEF"].table.GlyphClassDef.classDefs == {"V": 1, "a": 1}
    assert (
        font["GPOS"]
        .table.LookupList.Lookup[0]
        .SubTable[0]
        .PairSet[0]
        .PairValueRecord[0]
        .Value1.XAdvance
        == -12
    )


def test_write_skipexportglyphs(data_dir, tmp_path):
    shutil.copyfile(
        data_dir / "GlyphsUnitTestSans.glyphs", tmp_path / "GlyphsUnitTestSans.glyphs"
    )

    args = [
        "-g",
        str(tmp_path / "GlyphsUnitTestSans.glyphs"),
        "--master-dir",
        str(tmp_path / "master_ufos"),
        "--instance-dir",
        str(tmp_path / "instance_ufos"),
        "-o",
        "ufo",
    ]
    fontmake.__main__.main(args)

    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        tmp_path / "master_ufos" / "GlyphsUnitTestSans.designspace"
    )

    assert "public.skipExportGlyphs" in designspace.lib
    assert designspace.lib["public.skipExportGlyphs"] == [
        "_part.shoulder",
        "_part.stem",
    ]
    for path in (tmp_path / "master_ufos").glob("*.ufo"):
        with ufoLib2.Font.open(path) as ufo:
            assert "public.skipExportGlyphs" in ufo.lib

    shutil.rmtree(tmp_path / "master_ufos")

    fontmake.__main__.main(args + ["--no-write-skipexportglyphs"])

    designspace = designspaceLib.DesignSpaceDocument.fromfile(
        tmp_path / "master_ufos" / "GlyphsUnitTestSans.designspace"
    )
    assert "public.skipExportGlyphs" not in designspace.lib

    for path in (tmp_path / "master_ufos").glob("*.ufo"):
        with ufoLib2.Font.open(path) as ufo:
            assert "public.skipExportGlyphs" not in ufo.lib
            assert not ufo["_part.shoulder"].lib["com.schriftgestaltung.Glyphs.Export"]
            assert not ufo["_part.stem"].lib["com.schriftgestaltung.Glyphs.Export"]


def test_debug_feature_file(data_dir, tmp_path):
    shutil.copyfile(
        data_dir / "GlyphsUnitTestSans.glyphs", tmp_path / "GlyphsUnitTestSans.glyphs"
    )

    debug_feature_path = data_dir / "test.fea"

    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "GlyphsUnitTestSans.glyphs"),
            "--master-dir",
            "{tmp}",
            "--instance-dir",
            "{tmp}",
            "-i",
            "-o",
            "ttf",
            "--debug-feature-file",
            str(debug_feature_path),
        ]
    )

    with open(debug_feature_path, "r") as debug_feature_file:
        features = debug_feature_file.read()

    assert "### GlyphsUnitTestSans-Regular" in features
    assert "### GlyphsUnitTestSans-Black" in features


def test_ufo_to_static_otf_cff2(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "DesignspaceTest" / "MyFont-Light.ufo"),
            "-o",
            "otf-cff2",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.otf")} == {"MyFont-Light.otf"}


def test_static_otf_cffsubr_subroutinizer(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "DesignspaceTest" / "MyFont-Light.ufo"),
            "-o",
            "otf",
            "--subroutinizer",
            "cffsubr",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.otf")} == {"MyFont-Light.otf"}


def test_static_otf_compreffor_subroutinizer(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "DesignspaceTest" / "MyFont-Light.ufo"),
            "-o",
            "otf",
            "--subroutinizer",
            "compreffor",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.otf")} == {"MyFont-Light.otf"}


def test_main_with_feature_writer_none(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "MutatorSans" / "MutatorSansBoldCondensed.ufo"),
            "-o",
            "ttf",
            "--feature-writer",
            "None",
            "--output-dir",
            str(tmp_path),
        ]
    )

    test_output_ttf = fontTools.ttLib.TTFont(tmp_path / "MutatorSansBoldCondensed.ttf")
    assert "GPOS" not in test_output_ttf


def test_main_with_filter(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "DesignspaceTest" / "MyFont-Light.ufo"),
            "-o",
            "ttf",
            "--filter",
            "TransformationsFilter(OffsetX=100)",
            "--output-dir",
            str(tmp_path),
        ]
    )

    test_output_ttf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Light.ttf")
    hmtx = test_output_ttf["hmtx"]
    assert hmtx["l"] == (160, 170)
