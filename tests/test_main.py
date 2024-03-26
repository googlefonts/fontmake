import logging
import platform
import re
import shutil
import subprocess
import sys
from textwrap import dedent

import fontTools.designspaceLib as designspaceLib
import fontTools.ttLib
import pytest
import ufoLib2
from fontTools.misc.testTools import getXML
from ufo2ft.util import zip_strict

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
    glyph = test_output_ttf["glyf"]["l"]
    assert glyph.xMin == 50
    assert glyph.xMax == 170

    test_output_otf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.otf")
    assert test_output_otf["OS/2"].usWeightClass == 400
    glyph_set = test_output_otf.getGlyphSet()
    charstrings = list(test_output_otf["CFF "].cff.values())[0].CharStrings
    glyph = charstrings["l"]
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
    glyph = test_output_ttf["glyf"]["l"]
    assert glyph.xMin == 50
    assert glyph.xMax == 170

    test_output_otf = fontTools.ttLib.TTFont(tmp_path / "MyFont-Regular.otf")
    assert test_output_otf["OS/2"].usWeightClass == 400
    glyph_set = test_output_otf.getGlyphSet()
    charstrings = list(test_output_otf["CFF "].cff.values())[0].CharStrings
    glyph = charstrings["l"]
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


@pytest.mark.parametrize(
    "write_skipexportglyphs",
    [
        pytest.param(True, id="default"),
        pytest.param(False, id="no-write-skipexportglyphs"),
    ],
)
def test_keep_glyphs(data_dir, tmp_path, write_skipexportglyphs):
    shutil.copyfile(data_dir / "TestSubset2.glyphs", tmp_path / "TestSubset2.glyphs")

    args = [
        "-g",
        str(tmp_path / "TestSubset2.glyphs"),
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
            assert font.getGlyphOrder() == [".notdef", "space", "D"]


def test_shared_features_expansion(data_dir, tmp_path):
    shutil.copytree(data_dir / "DesignspaceTestSharedFeatures", tmp_path / "sources")

    fontmake.__main__.main(
        [
            "-m",
            str(tmp_path / "sources" / "DesignspaceTestSharedFeatures.designspace"),
            "-i",
            "--expand-features-to-instances",
            "-o",
            "ufo",
            "--output-dir",
            str(tmp_path),
        ]
    )

    test_feature_file = tmp_path / "DesignspaceTest-Light.ufo/features.fea"
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


def test_glyph_data(data_dir, tmp_path):
    shutil.copyfile(
        data_dir / "GlyphsUnitTestSans.glyphs", tmp_path / "GlyphsUnitTestSans.glyphs"
    )
    shutil.copyfile(data_dir / "GlyphData.xml", tmp_path / "GlyphData.xml")

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

    for path in (tmp_path / "master_ufos").glob("*.ufo"):
        with ufoLib2.Font.open(path) as ufo:
            assert "public.openTypeCategories" in ufo.lib
            assert ufo.lib["public.openTypeCategories"].get("fatha-ar") == "mark"

            fatha = ufo["fatha-ar"]
            assert fatha.width == 0
            assert "com.schriftgestaltung.Glyphs.originalWidth" in fatha.lib

    shutil.rmtree(tmp_path / "master_ufos")

    fontmake.__main__.main(
        args
        + [
            "--glyph-data",
            str(tmp_path / "GlyphData.xml"),
        ]
    )

    for path in (tmp_path / "master_ufos").glob("*.ufo"):
        with ufoLib2.Font.open(path) as ufo:
            assert "public.openTypeCategories" in ufo.lib
            assert ufo.lib["public.openTypeCategories"].get("fatha-ar") is None

            fatha = ufo["fatha-ar"]
            assert fatha.width != 0
            assert "com.schriftgestaltung.Glyphs.originalWidth" not in fatha.lib
            assert fatha.lib.get("com.schriftgestaltung.Glyphs.category") == "Letter"
            assert fatha.lib.get("com.schriftgestaltung.Glyphs.subCategory") is None


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


def test_ufoz_to_static_otf_cff2(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-u",
            str(data_dir / "DesignspaceTest" / "MyFont-Light.ufoz"),
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
            str(tmp_path / "output" / "MySingleVF.ttf"),
        ]
    )

    # 'output' subfolder was created automatically
    assert (tmp_path / "output" / "MySingleVF.ttf").exists()


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


def test_main_glyphspackage(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-g",
            str(data_dir / "GlyphsUnitTestSans3.glyphspackage"),
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert (tmp_path / "GlyphsUnitTestSans-Light.ttf").exists()
    assert (tmp_path / "GlyphsUnitTestSans-Regular.ttf").exists()
    assert (tmp_path / "GlyphsUnitTestSans-Bold.ttf").exists()


def test_timing_logger(data_dir, tmp_path):
    # check that --timing flag logs timing-related DEBUG messages even if the
    # logging level (as set by --verbose flag) is higher
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fontmake",
            "--timing",
            "--verbose",
            "CRITICAL",
            "-m",
            str(data_dir / "DesignspaceTest" / "DesignspaceTest.designspace"),
            "-i",
            "-o",
            "ttf",
            "--output-dir",
            str(tmp_path),
        ],
        capture_output=True,
        check=True,
    )

    assert re.search(
        r"^DEBUG:fontmake.timer:Took [\.0-9]+s to run 'save_otfs'\r?$",
        result.stderr.decode(),
        flags=re.MULTILINE,
    )


@pytest.fixture(params=["package", "zip", "json"])
def ufo_structure(request):
    if request.param == "json":
        # skip if ufoLib2's extra dep is not installed
        pytest.importorskip("cattrs")
    return request.param


@pytest.mark.parametrize("interpolate", [False, True])
def test_main_export_custom_ufo_structure(
    data_dir, tmp_path, ufo_structure, interpolate
):
    args = [
        str(data_dir / "GlyphsUnitTestSans.glyphs"),
        "-o",
        "ufo",
        "--output-dir",
        str(tmp_path),
        "--ufo-structure",
        ufo_structure,
    ]
    if interpolate:
        args.append("-i")
    else:
        # strictly not needed, added just to make Windows happy about relative
        # instance.filename when designspace is written to a different mount point
        args.extend(["--instance-dir", str(tmp_path)])

    fontmake.__main__.main(args)

    ext = {"package": ".ufo", "zip": ".ufoz", "json": ".ufo.json"}[ufo_structure]

    for style in ["Light", "Regular", "Bold"]:
        assert (tmp_path / f"GlyphsUnitTestSans-{style}").with_suffix(ext).exists()

    if interpolate:
        for style in ["Thin", "ExtraLight", "Medium", "Black", "Web"]:
            assert (tmp_path / f"GlyphsUnitTestSans-{style}").with_suffix(ext).exists()


@pytest.mark.parametrize("ufo_structure", ["zip", "json"])
def test_main_build_from_custom_ufo_structure(data_dir, tmp_path, ufo_structure):
    pytest.importorskip("cattrs")

    # export designspace pointing to {json,zip}-flavored source UFOs
    fontmake.__main__.main(
        [
            str(data_dir / "GlyphsUnitTestSans.glyphs"),
            "-o",
            "ufo",
            "--output-dir",
            str(tmp_path / "master_ufos"),
            "--ufo-structure",
            ufo_structure,
            # makes Windows happy about relative instance.filename across drives
            "--instance-dir",
            str(tmp_path / "instance_ufos"),
        ]
    )

    # interpolate one static TTF instance from this designspace
    fontmake.__main__.main(
        [
            str(tmp_path / "master_ufos" / "GlyphsUnitTestSans.designspace"),
            "-o",
            "ttf",
            "-i",
            "Glyphs Unit Test Sans Extra Light",
            "--output-path",
            str(tmp_path / "instance_ttfs" / "GlyphsUnitTestSans-ExtraLight.ttf"),
        ]
    )

    assert len(list((tmp_path / "instance_ttfs").glob("*.ttf"))) == 1
    assert (tmp_path / "instance_ttfs" / "GlyphsUnitTestSans-ExtraLight.ttf").exists()

    # build one {json,zip} UFO => OTF
    ext = {"json": ".ufo.json", "zip": ".ufoz"}[ufo_structure]
    fontmake.__main__.main(
        [
            str(tmp_path / "master_ufos" / f"GlyphsUnitTestSans-Regular{ext}"),
            "-o",
            "otf",
            "--output-path",
            str(tmp_path / "master_otfs" / "GlyphsUnitTestSans-Regular.otf"),
        ]
    )

    assert len(list((tmp_path / "master_otfs").glob("*.otf"))) == 1
    assert (tmp_path / "master_otfs" / "GlyphsUnitTestSans-Regular.otf").exists()


@pytest.mark.parametrize("indent_json", [False, True])
def test_main_export_ufo_json_with_indentation(data_dir, tmp_path, indent_json):
    pytest.importorskip("cattrs")

    fontmake.__main__.main(
        [
            str(data_dir / "GlyphsUnitTestSans.glyphs"),
            "-o",
            "ufo",
            "--output-dir",
            str(tmp_path / "master_ufos"),
            "--ufo-structure",
            "json",
            # makes Windows happy about relative instance.filename across drives
            "--instance-dir",
            str(tmp_path / "instance_ufos"),
        ]
        + (["--indent-json"] if indent_json else [])
    )

    regular_ufo = tmp_path / "master_ufos" / "GlyphsUnitTestSans-Regular.ufo.json"
    assert (regular_ufo).exists()

    if indent_json:
        assert regular_ufo.read_text().startswith('{\n  "features"')
    else:
        assert regular_ufo.read_text().startswith('{"features"')


def assert_tuple_variation_regions(tvs, expected_regions):
    for tv, expected_region in zip_strict(tvs, expected_regions):
        assert set(tv.axes.keys()) == set(expected_region.keys())
        for axis in tv.axes:
            assert tv.axes[axis] == pytest.approx(expected_region[axis], rel=1e-3)


def test_main_sparse_composite_glyphs_variable_ttf(data_dir, tmp_path):
    fontmake.__main__.main(
        [
            "-g",
            str(data_dir / "IntermediateComponents.glyphs"),
            "-o",
            "variable",
            "--output-path",
            str(tmp_path / "IntermediateComponents-VF.ttf"),
            "--no-production-names",
        ]
    )

    vf = fontTools.ttLib.TTFont(tmp_path / "IntermediateComponents-VF.ttf")
    assert [a.axisTag for a in vf["fvar"].axes] == ["wght"]
    glyf = vf["glyf"]
    gvar = vf["gvar"]

    # 'aacute' defines more masters than its components; no problem
    aacute = glyf["aacute"]
    assert aacute.isComposite()
    assert [c.glyphName for c in aacute.components] == ["a", "acutecomb"]
    assert_tuple_variation_regions(
        gvar.variations["aacute"],
        [{"wght": (0.0, 0.2, 1.0)}, {"wght": (0.2, 1.0, 1.0)}],
    )
    assert_tuple_variation_regions(gvar.variations["a"], [{"wght": (0.0, 1.0, 1.0)}])
    assert_tuple_variation_regions(
        gvar.variations["acutecomb"], [{"wght": (0.0, 1.0, 1.0)}]
    )

    # other composites that use 'aacute' as component don't need additional masters
    # as long as they stay composite
    aacutecommaaccent = glyf["aacutecommaaccent"]
    assert aacutecommaaccent.isComposite()
    assert [c.glyphName for c in aacutecommaaccent.components] == [
        "aacute",
        "commaaccentcomb",
    ]
    for name in ("aacutecommaaccent", "commaaccentcomb"):
        assert_tuple_variation_regions(
            gvar.variations[name], [{"wght": (0.0, 1.0, 1.0)}]
        )

    # 'i' gets decomposed to simple glyph because it originally had a mix of contour
    # and component ('idotless'); it also inherits an additional master from the latter
    i = glyf["i"]
    assert i.numberOfContours == 2
    idotless = glyf["idotless"]
    assert idotless.numberOfContours == 1
    for name in ("i", "idotless"):
        assert_tuple_variation_regions(
            gvar.variations[name],
            [
                {"wght": (0.0, 0.6, 1.0)},
                {"wght": (0.6, 1.0, 1.0)},
            ],
        )

    # but 'iacute' and 'imacron' using 'idotless' as a component don't need to be
    # decomposed, nor do they inherit any additional master
    for name in ("iacute", "imacron"):
        glyph = glyf[name]
        assert "idotless" in {c.glyphName for c in glyph.components}
        assert glyph.isComposite()
        assert_tuple_variation_regions(
            gvar.variations[name], [{"wght": (0.0, 1.0, 1.0)}]
        )

    # nor does 'iacutecedilla' which uses 'iacute' as components
    iacutecedilla = glyf["iacutecedilla"]
    assert iacutecedilla.isComposite()
    assert [c.glyphName for c in iacutecedilla.components] == ["iacute", "cedillacomb"]
    for name in ("iacutecedilla", "iacute", "cedillacomb"):
        assert_tuple_variation_regions(
            gvar.variations[name], [{"wght": (0.0, 1.0, 1.0)}]
        )

    # 'nmacronbelow' is similar to 'aacute', defines more masters than its components
    nmacronbelow = glyf["nmacronbelow"]
    assert nmacronbelow.isComposite()
    assert [c.glyphName for c in nmacronbelow.components] == ["n", "macronbelowcomb"]
    assert_tuple_variation_regions(
        gvar.variations["nmacronbelow"],
        [
            {"wght": (0.0, 0.4, 1.0)},
            {"wght": (0.4, 1.0, 1.0)},
        ],
    )
    assert_tuple_variation_regions(gvar.variations["n"], [{"wght": (0.0, 1.0, 1.0)}])
    assert_tuple_variation_regions(
        gvar.variations["macronbelowcomb"], [{"wght": (0.0, 1.0, 1.0)}]
    )

    # 'aacutecedilla' originally comprised 'aacute' and 'cedillacomb' components, but
    # since the latter had a 2x2 transform in one intermediate master only (wght=0.4),
    # it gets decomposed; it also inherits the additional master from 'aacute' (wght=0.2)
    aacutecedilla = glyf["aacutecedilla"]
    assert aacutecedilla.numberOfContours == 4
    assert_tuple_variation_regions(
        gvar.variations["aacutecedilla"],
        [
            {"wght": (0.0, 0.2, 1.0)},
            {"wght": (0.2, 0.4, 1.0)},
            {"wght": (0.4, 1.0, 1.0)},
        ],
    )


def test_main_sparse_composite_glyphs_variable_cff2(data_dir, tmp_path):
    # CFF/CFF2 have no concept of 'components' in the TrueType sense, so all glyphs
    # will be decomposed into contours
    fontmake.__main__.main(
        [
            "-g",
            str(data_dir / "IntermediateComponents.glyphs"),
            "-o",
            "variable-cff2",
            "--output-path",
            str(tmp_path / "IntermediateComponents-VF.otf"),
            "--no-production-names",
        ]
    )

    vf = fontTools.ttLib.TTFont(tmp_path / "IntermediateComponents-VF.otf")
    axes = vf["fvar"].axes
    assert [a.axisTag for a in axes] == ["wght"]

    font = vf["CFF2"].cff
    font.desubroutinize()
    top_dict = font.topDictIndex[0]
    varstore = top_dict.VarStore.otVarStore
    vardata = varstore.VarData
    regions = varstore.VarRegionList.Region
    charstrings = top_dict.CharStrings

    def assert_charstring_regions(charstring, expected_regions):
        vsindex = 0
        for i, token in enumerate(charstring.program):
            if token == "vsindex":
                vsindex = charstring.program[i - 1]
                break
        cs_regions = [
            regions[ri].get_support(axes) for ri in vardata[vsindex].VarRegionIndex
        ]
        for cs_region, expected_region in zip_strict(cs_regions, expected_regions):
            assert set(cs_region.keys()) == set(expected_region.keys())
            for axis in cs_region:
                assert cs_region[axis] == pytest.approx(expected_region[axis], rel=1e-3)

    # 'aacute' defines an extra intermediate master not present in 'a' or 'acutecomb',
    # these get interpolated on the fly as 'aacute' gets decomposed; all other composite
    # glyphs in turn using 'aacute' will similarly gain the extra master
    for name in ("a", "acutecomb"):
        assert_charstring_regions(charstrings[name], [{"wght": (0.0, 1.0, 1.0)}])
    for name in ("aacute", "aacutecommaaccent", "aacutecommaaccentcedilla"):
        assert_charstring_regions(
            charstrings[name],
            [
                {"wght": (0.0, 0.2, 1.0)},
                {"wght": (0.2, 1.0, 1.0)},
            ],
        )
    # 'idotless' "infects" all the composite glyphs using it as a component with its
    # extra master
    for name in (
        "idotless",
        "i",
        "iacute",
        "iacutecedilla",
        "icedilla",
        "icommaaccent",
    ):
        assert_charstring_regions(
            charstrings[name],
            [
                {"wght": (0.0, 0.6, 1.0)},
                {"wght": (0.6, 1.0, 1.0)},
            ],
        )
    # 'imacron' etc. inherit extra masters from both 'idotless' and 'macroncomb'
    assert_charstring_regions(
        charstrings["macroncomb"],
        [{"wght": (0.0, 0.8, 1.0)}, {"wght": (0.8, 1.0, 1.0)}],
    )
    for name in ("imacron", "imacroncommaaccent"):
        assert_charstring_regions(
            charstrings[name],
            [
                {"wght": (0.0, 0.6, 1.0)},
                {"wght": (0.6, 0.8, 1.0)},
                {"wght": (0.8, 1.0, 1.0)},
            ],
        )
    # nothing special here
    for name in ("n", "nacute", "ncommaaccent", "acedilla"):
        assert_charstring_regions(charstrings[name], [{"wght": (0.0, 1.0, 1.0)}])
    # 'nmacronbelow' defines an extra master (peak wght=0.4) not present in 'n' or
    # 'macronbelowcomb' so it ends up with 3 regions (one comes from 'macronbelowcomb')
    for name in ("nmacronbelow", "nacutemacronbelow"):
        assert_charstring_regions(
            charstrings[name],
            [
                {"wght": (0.0, 0.4, 1.0)},
                {"wght": (0.4, 0.8, 1.0)},
                {"wght": (0.8, 1.0, 1.0)},
            ],
        )
    # 'aacutecedilla' has one intermediate master of its own, plus inherits an other
    # from 'aacute'
    assert_charstring_regions(
        charstrings["aacutecedilla"],
        [
            {"wght": (0.0, 0.2, 1.0)},
            {"wght": (0.2, 0.4, 1.0)},
            {"wght": (0.4, 1.0, 1.0)},
        ],
    )
    # this monster combines the two additional masters from 'aacutecedilla' and the
    # one from 'macronbelowcomb'
    assert_charstring_regions(
        charstrings["aacutemacronbelowcedilla"],
        [
            {"wght": (0.0, 0.2, 1.0)},
            {"wght": (0.2, 0.4, 1.0)},
            {"wght": (0.4, 0.8, 1.0)},
            {"wght": (0.8, 1.0, 1.0)},
        ],
    )
