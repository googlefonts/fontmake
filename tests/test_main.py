import logging
import platform
import shutil
from textwrap import dedent

import fontTools.designspaceLib as designspaceLib
import fontTools.ttLib
import pytest
import ufoLib2
from fontTools.misc.testTools import getXML

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


def test_interpolation_designspace_5(data_dir, tmp_path):
    shutil.copytree(data_dir / "MutatorSansLite", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "MutatorFamily_v5_discrete_axis.designspace"),
            "-i",
            ".*Light Condensed",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "MutatorMathTest-Sans Light Condensed.ttf",
        "MutatorMathTest-Serif Light Condensed.otf",
        "MutatorMathTest-Sans Light Condensed.otf",
        "MutatorMathTest-Serif Light Condensed.ttf",
    }


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


# TODO(anthrotype): Re-enable this test once upstream issue is fixed:
# https://github.com/fonttools/ttfautohint-py/issues/11
@pytest.mark.skipif(
    platform.python_implementation() == "PyPy",
    reason="ttfautohint-py doesn't work with pypy",
)
@pytest.mark.parametrize(
    "autohint_options",
    [
        (),
        ("-a",),
        ("--autohint", "-D latn"),
        ("-A",),
        ("--no-autohint",),
    ],
)
def test_autohinting(data_dir, tmp_path, autohint_options):
    shutil.copytree(data_dir / "AutohintingTest", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-g",
            str(tmp_path / "sources" / "Padyakke.glyphs"),
            "-o",
            "ttf",
            "-i",
            "--output-dir",
            str(tmp_path),
            *autohint_options,
        ]
    )

    assert {p.name for p in tmp_path.glob("*.*")} == {
        "PadyakkeExpandedOne-Regular.ttf",
    }

    test_output_ttf = fontTools.ttLib.TTFont(
        tmp_path / "PadyakkeExpandedOne-Regular.ttf"
    )

    if not {"-A", "--no-autohint"}.intersection(autohint_options):
        assert "fpgm" in test_output_ttf  # hinted
    else:
        assert "fpgm" not in test_output_ttf  # unhinted


def test_main_designspace_v5_builds_STAT(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "--verbose",
            "DEBUG",
            "-m",
            str(
                data_dir
                / "MutatorSansLite"
                / "MutatorSans_v5_implicit_one_vf.designspace"
            ),
            "-o",
            "variable",
            "--output-dir",
            str(tmp_path),
        ]
    )
    test_output_ttf = fontTools.ttLib.TTFont(
        tmp_path / "MutatorSans_v5_implicit_one_vf-VF.ttf"
    )
    stat = test_output_ttf["STAT"]
    assert (
        getXML(stat.toXML)
        == dedent(
            """\
            <Version value="0x00010002"/>
            <DesignAxisRecordSize value="8"/>
            <!-- DesignAxisCount=2 -->
            <DesignAxisRecord>
              <Axis index="0">
                <AxisTag value="wght"/>
                <AxisNameID value="274"/>
                <AxisOrdering value="0"/>
              </Axis>
              <Axis index="1">
                <AxisTag value="wdth"/>
                <AxisNameID value="276"/>
                <AxisOrdering value="1"/>
              </Axis>
            </DesignAxisRecord>
            <!-- AxisValueCount=8 -->
            <AxisValueArray>
              <AxisValue index="0" Format="4">
                <!-- AxisCount=2 -->
                <Flags value="0"/>
                <ValueNameID value="280"/>
                <AxisValueRecord index="0">
                  <AxisIndex value="0"/>
                  <Value value="610.2436"/>
                </AxisValueRecord>
                <AxisValueRecord index="1">
                  <AxisIndex value="1"/>
                  <Value value="158.9044"/>
                </AxisValueRecord>
              </AxisValue>
              <AxisValue index="1" Format="4">
                <!-- AxisCount=2 -->
                <Flags value="0"/>
                <ValueNameID value="281"/>
                <AxisValueRecord index="0">
                  <AxisIndex value="0"/>
                  <Value value="642.2196"/>
                </AxisValueRecord>
                <AxisValueRecord index="1">
                  <AxisIndex value="1"/>
                  <Value value="159.1956"/>
                </AxisValueRecord>
              </AxisValue>
              <AxisValue index="2" Format="2">
                <AxisIndex value="0"/>
                <Flags value="0"/>
                <ValueNameID value="275"/>
                <NominalValue value="300.0"/>
                <RangeMinValue value="300.0"/>
                <RangeMaxValue value="400.0"/>
              </AxisValue>
              <AxisValue index="3" Format="2">
                <AxisIndex value="0"/>
                <Flags value="0"/>
                <ValueNameID value="266"/>
                <NominalValue value="500.0"/>
                <RangeMinValue value="400.0"/>
                <RangeMaxValue value="600.0"/>
              </AxisValue>
              <AxisValue index="4" Format="2">
                <AxisIndex value="0"/>
                <Flags value="0"/>
                <ValueNameID value="269"/>
                <NominalValue value="700.0"/>
                <RangeMinValue value="600.0"/>
                <RangeMaxValue value="700.0"/>
              </AxisValue>
              <AxisValue index="5" Format="2">
                <AxisIndex value="1"/>
                <Flags value="0"/>
                <ValueNameID value="277"/>
                <NominalValue value="50.0"/>
                <RangeMinValue value="50.0"/>
                <RangeMaxValue value="75.0"/>
              </AxisValue>
              <AxisValue index="6" Format="2">
                <AxisIndex value="1"/>
                <Flags value="2"/>  <!-- ElidableAxisValueName -->
                <ValueNameID value="278"/>
                <NominalValue value="100.0"/>
                <RangeMinValue value="75.0"/>
                <RangeMaxValue value="125.0"/>
              </AxisValue>
              <AxisValue index="7" Format="2">
                <AxisIndex value="1"/>
                <Flags value="0"/>
                <ValueNameID value="279"/>
                <NominalValue value="200.0"/>
                <RangeMinValue value="125.0"/>
                <RangeMaxValue value="200.0"/>
              </AxisValue>
            </AxisValueArray>
            <ElidedFallbackNameID value="273"/>"""
        ).splitlines()
    )


def test_main_designspace_v5_builds_all_vfs(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-m",
            str(
                data_dir
                / "MutatorSansLite"
                / "MutatorFamily_v5_discrete_axis.designspace"
            ),
            "-o",
            "variable",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert (tmp_path / "MutatorSansVariable_Weight_Width.ttf").exists()
    assert (tmp_path / "MutatorSansVariable_Weight.ttf").exists()
    assert (tmp_path / "MutatorSansVariable_Width.ttf").exists()
    assert (tmp_path / "MutatorSerifVariable_Width.ttf").exists()


def test_main_designspace_v5_select_no_matching_fonts_shows_nice_message(
    data_dir, tmp_path, caplog
):
    with caplog.at_level(logging.WARNING):
        fontmake.__main__.main(
            [
                "-m",
                str(
                    data_dir
                    / "MutatorSansLite"
                    / "MutatorFamily_v5_discrete_axis.designspace"
                ),
                "--variable-fonts",
                "NothingMatchesThisRegex",
                "-o",
                "variable",
                "--output-dir",
                str(tmp_path),
            ]
        )

    assert "No variable fonts matching NothingMatchesThisRegex" in caplog.text

    # Nothing gets built
    assert not (tmp_path / "MutatorSansVariable_Weight_Width.ttf").exists()
    assert not (tmp_path / "MutatorSansVariable_Weight.ttf").exists()
    assert not (tmp_path / "MutatorSansVariable_Width.ttf").exists()
    assert not (tmp_path / "MutatorSerifVariable_Width.ttf").exists()


def test_main_designspace_v5_select_vfs_to_build(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-m",
            str(
                data_dir
                / "MutatorSansLite"
                / "MutatorFamily_v5_discrete_axis.designspace"
            ),
            "--variable-fonts",
            "MutatorSansVariable_Weight.*",
            "-o",
            "variable",
            "--output-dir",
            str(tmp_path),
        ]
    )

    assert (tmp_path / "MutatorSansVariable_Weight_Width.ttf").exists()
    assert (tmp_path / "MutatorSansVariable_Weight.ttf").exists()
    assert not (tmp_path / "MutatorSansVariable_Width.ttf").exists()
    assert not (tmp_path / "MutatorSerifVariable_Width.ttf").exists()


def test_main_designspace_v5_can_use_output_path_with_1_vf(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-m",
            str(
                data_dir / "MutatorSansLite" / "MutatorSans_v5_several_vfs.designspace"
            ),
            "-o",
            "variable",
            "--variable-fonts",
            "MutatorSansVariable_Width",
            "--output-path",
            str(tmp_path / "MySingleVF.ttf"),
        ]
    )

    assert (tmp_path / "MySingleVF.ttf").exists()


def test_main_designspace_v5_dont_interpolate_discrete_axis(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-m",
            str(
                data_dir
                / "MutatorSansLite"
                / "MutatorSans_v5_several_vfs_discrete_axis.designspace"
            ),
            "-o",
            "variable",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert (tmp_path / "MutatorSansCondensedVariable_Weight.ttf").exists()
    assert (tmp_path / "MutatorSansExtendedVariable_Weight.ttf").exists()
