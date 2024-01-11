# Copyright 2015 Google Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import enum
import glob
import logging
import math
import os
import shutil
import tempfile
from collections import OrderedDict
from functools import partial
from pathlib import Path
from re import fullmatch

import attr
import ufo2ft
import ufo2ft.errors
import ufoLib2
from fontTools import designspaceLib
from fontTools.designspaceLib.split import splitInterpolable
from fontTools.misc.cliTools import makeOutputFileName
from fontTools.misc.loggingTools import Timer
from fontTools.misc.plistlib import load as readPlist
from fontTools.ttLib import TTFont
from fontTools.varLib.interpolate_layout import interpolate_layout
from ufo2ft import CFFOptimization
from ufo2ft.featureCompiler import parseLayoutFeatures
from ufo2ft.featureWriters import FEATURE_WRITERS_KEY, loadFeatureWriters
from ufo2ft.filters import FILTERS_KEY, loadFilters
from ufo2ft.util import makeOfficialGlyphOrder

from fontmake import instantiator
from fontmake.compatibility import CompatibilityChecker
from fontmake.errors import FontmakeError, TTFAError
from fontmake.ttfautohint import ttfautohint

logger = logging.getLogger(__name__)
timer = Timer(logging.getLogger("fontmake.timer"), level=logging.DEBUG)

PUBLIC_PREFIX = "public."
GLYPHS_PREFIX = "com.schriftgestaltung."
# for glyphsLib < 2.3.0
KEEP_GLYPHS_OLD_KEY = GLYPHS_PREFIX + "Keep Glyphs"
REMOVE_GLYPHS_OLD_KEY = GLYPHS_PREFIX + "Remove Glyphs"
# for glyphsLib >= 2.3.0
KEEP_GLYPHS_NEW_KEY = (
    GLYPHS_PREFIX + "customParameter.InstanceDescriptorAsGSInstance.Keep Glyphs"
)
REMOVE_GLYPHS_NEW_KEY = (
    GLYPHS_PREFIX + "customParameter.InstanceDescriptorAsGSInstance.Remove Glyphs"
)
GLYPH_EXPORT_KEY = GLYPHS_PREFIX + "Glyphs.Export"
COMPAT_CHECK_KEY = GLYPHS_PREFIX + "customParameter.GSFont.Enforce Compatibility Check"

INTERPOLATABLE_OUTPUTS = frozenset(
    ["ttf-interpolatable", "otf-interpolatable", "variable", "variable-cff2"]
)

AUTOHINTING_PARAMETERS = (
    GLYPHS_PREFIX + "customParameter.InstanceDescriptorAsGSInstance.TTFAutohint options"
)

# tempLib keys for fontmake's internal use only, won't be saved to disk
INSTANCE_LOCATION_KEY = "com.github.googlefonts.fontmake.instance_location"
INSTANCE_FILENAME_KEY = "com.github.googlefonts.fontmake.instance_filename"


UFO_STRUCTURE_EXTENSIONS = {
    "package": ".ufo",
    "zip": ".ufoz",
    "json": ".ufo.json",
}


class CurveConversion(enum.Enum):
    # convert all cubic Bezier curves to quadratic splines: glyf format 0
    ALL_CUBIC_TO_QUAD = "cu2qu"
    # convert cubic curves to quadratic when more economical: glyf format 1
    MIXED_CUBIC_TO_QUAD = "mixed"
    # skip conversion, treat original curves as quadratic: glyf format 0
    KEEP_QUAD = "keep-quad"
    # skip conversion, treat original curves as cubic or mixed: glyf format 1
    KEEP_CUBIC = "keep-cubic"

    @classmethod
    def default(cls):
        return cls.ALL_CUBIC_TO_QUAD

    @property
    def convertCubics(self):
        return self in (
            CurveConversion.ALL_CUBIC_TO_QUAD,
            CurveConversion.MIXED_CUBIC_TO_QUAD,
        )

    @property
    def allQuadratic(self):
        return self in (
            CurveConversion.ALL_CUBIC_TO_QUAD,
            CurveConversion.KEEP_QUAD,
        )


def needs_subsetting(ufo):
    if KEEP_GLYPHS_OLD_KEY in ufo.lib or KEEP_GLYPHS_NEW_KEY in ufo.lib:
        return True
    if REMOVE_GLYPHS_OLD_KEY in ufo.lib or REMOVE_GLYPHS_NEW_KEY in ufo.lib:
        return True
    if any(glyph.lib.get(GLYPH_EXPORT_KEY, True) is False for glyph in ufo):
        return True
    return False


class FontProject:
    """Provides methods for building fonts."""

    def __init__(
        self,
        timing=None,  # deprecated
        verbose=None,  # deprecated
        validate_ufo=False,
    ):
        if verbose is not None or timing is not None:
            from warnings import warn

            from fontmake.__main__ import _configure_logging

            warn(
                "The 'verbose'/'timing' arguments are deprecated. "
                "Logging configuration is global and should not be "
                "specified in the FontProject constructor. "
                "Use the logging API to configure fontmake's loggers "
                "for your application. E.g. fontmake main() function "
                "uses logging.basicConfig().",
                UserWarning,
                stacklevel=2,
            )

            _configure_logging(verbose, timing)

        logger.debug(
            "ufoLib UFO validation is %s", "enabled" if validate_ufo else "disabled"
        )
        self.validate_ufo = validate_ufo

    def open_ufo(self, path):
        try:
            path = Path(path)
            if path.suffix == ".json":
                with open(path, "rb") as f:
                    # pylint: disable=no-member
                    return ufoLib2.Font.json_load(f)  # type: ignore
            return ufoLib2.Font.open(path, validate=self.validate_ufo)
        except Exception as e:
            raise FontmakeError("Reading UFO source failed", path) from e

    @staticmethod
    def _fix_ufo_path(path, ufo_structure):
        """Normalizes UFO path and updates extension suffix to match its structure"""
        return os.path.normpath(
            Path(path).with_suffix(UFO_STRUCTURE_EXTENSIONS[ufo_structure])
        )

    def save_ufo_as(self, font, path, ufo_structure="package", indent_json=False):
        try:
            path = _ensure_parent_dir(path)
            if ufo_structure == "json":
                with open(path, "wb") as f:
                    # pylint: disable=no-member
                    font.json_dump(
                        f,
                        # orjson only supports either 2 or none
                        indent=2 if indent_json else None,
                        # makes output deterministic
                        sort_keys=True,
                    )  # type: ignore
            else:
                font.save(
                    path,
                    overwrite=True,
                    validate=self.validate_ufo,
                    structure=ufo_structure,
                )
        except Exception as e:
            raise FontmakeError("Writing UFO source failed", path) from e

    @timer()
    def build_master_ufos(
        self,
        glyphs_path,
        designspace_path=None,
        master_dir=None,
        instance_dir=None,
        family_name=None,
        mti_source=None,
        write_skipexportglyphs=True,
        generate_GDEF=True,
        ufo_structure="package",
        indent_json=False,
        glyph_data=None,
        save_ufos=True,
    ):
        """Build UFOs and designspace from Glyphs source."""
        import glyphsLib

        if master_dir is None:
            master_dir = self._output_dir("ufo")
        if instance_dir is None:
            instance_dir = self._output_dir("ufo", is_instance=True)

        if designspace_path is not None:
            designspace_dir = os.path.dirname(designspace_path)
        else:
            designspace_dir = master_dir
        # glyphsLib.to_designspace expects instance_dir to be relative to the
        # designspace's own directory
        try:
            instance_dir = os.path.relpath(instance_dir, designspace_dir)
        except ValueError as e:
            raise FontmakeError(
                "Can't make instance_dir path relative to designspace. "
                "If on Windows, please make sure that --instance-dir, "
                "--master-dir and --designspace-path are on the same mount drive "
                "(e.g. C: or D:)",
                glyphs_path,
            ) from e

        try:
            font = glyphsLib.load(glyphs_path)
        except Exception as e:
            raise FontmakeError("Loading Glyphs file failed", glyphs_path) from e

        designspace = glyphsLib.to_designspace(
            font,
            family_name=family_name,
            instance_dir=instance_dir,
            write_skipexportglyphs=write_skipexportglyphs,
            ufo_module=ufoLib2,
            generate_GDEF=generate_GDEF,
            store_editor_state=False,
            minimal=True,
            glyph_data=glyph_data,
        )

        masters = {}
        # multiple sources can have the same font/filename (but different layer),
        # we want to save a font only once
        for source in designspace.sources:
            ufo_path = self._fix_ufo_path(
                os.path.join(master_dir, source.filename), ufo_structure
            )
            source.path = ufo_path
            # relative 'filename' would be auto-updated upon writing the designspace
            # but we may not always write one out, thus we keep it up-to-date
            source.filename = os.path.relpath(ufo_path, designspace_dir)
            if ufo_path in masters:
                assert source.font is masters[ufo_path]
                continue
            masters[ufo_path] = source.font

        if mti_source:
            self.add_mti_features_to_master_ufos(mti_source, masters)

        save_ds = designspace_path is not None or save_ufos
        if designspace_path is None:
            designspace_path = os.path.join(master_dir, designspace.filename)

        if save_ds:
            logger.info("Saving %s", designspace_path)
            designspace.write(_ensure_parent_dir(designspace_path))
        else:
            designspace.path = designspace_path

        if save_ufos:
            for ufo_path, ufo in masters.items():
                logger.info("Saving %s", ufo_path)
                self.save_ufo_as(ufo, ufo_path, ufo_structure, indent_json)

        return designspace

    @timer()
    def add_mti_features_to_master_ufos(self, mti_source, masters):
        mti_dir = os.path.dirname(mti_source)
        with open(mti_source, "rb") as mti_file:
            mti_paths = readPlist(mti_file)
        for master_path, master in masters.items():
            key = os.path.basename(master_path).rstrip(".ufo")
            for table, path in mti_paths[key].items():
                with open(os.path.join(mti_dir, path), "rb") as mti_source:
                    ufo_path = (
                        "com.github.googlei18n.ufo2ft.mtiFeatures/%s.mti"
                        % table.strip()
                    )
                    master.data[ufo_path] = mti_source.read()
                # If we have MTI sources, any Adobe feature files derived from
                # the Glyphs file should be ignored. We clear it here because
                # it only contains junk information anyway.
                master.features.text = ""

    def build_otfs(self, ufos, **kwargs):
        """Build OpenType binaries with CFF outlines."""
        self.save_otfs(ufos, **kwargs)

    def build_ttfs(self, ufos, **kwargs):
        """Build OpenType binaries with TrueType outlines."""
        self.save_otfs(ufos, ttf=True, **kwargs)

    def _build_interpolatable_masters(
        self,
        designspace,
        ttf,
        use_production_names=None,
        reverse_direction=True,
        ttf_curves=CurveConversion.ALL_CUBIC_TO_QUAD,
        conversion_error=None,
        feature_writers=None,
        cff_round_tolerance=None,
        debug_feature_file=None,
        fea_include_dir=None,
        flatten_components=False,
        filters=None,
        auto_use_my_metrics=True,
        **kwargs,
    ):
        if ttf:
            ttf_curves = CurveConversion(ttf_curves)
            return ufo2ft.compileInterpolatableTTFsFromDS(
                designspace,
                useProductionNames=use_production_names,
                reverseDirection=reverse_direction,
                convertCubics=ttf_curves.convertCubics,
                allQuadratic=ttf_curves.allQuadratic,
                cubicConversionError=conversion_error,
                featureWriters=feature_writers,
                debugFeatureFile=debug_feature_file,
                feaIncludeDir=fea_include_dir,
                filters=filters,
                flattenComponents=flatten_components,
                autoUseMyMetrics=auto_use_my_metrics,
                inplace=True,
            )
        else:
            return ufo2ft.compileInterpolatableOTFsFromDS(
                designspace,
                useProductionNames=use_production_names,
                roundTolerance=cff_round_tolerance,
                featureWriters=feature_writers,
                debugFeatureFile=debug_feature_file,
                feaIncludeDir=fea_include_dir,
                filters=filters,
                inplace=True,
            )

    def build_interpolatable_ttfs(self, designspace, **kwargs):
        """Build OpenType binaries with interpolatable TrueType outlines
        from DesignSpaceDocument object.
        """
        return self._build_interpolatable_masters(designspace, ttf=True, **kwargs)

    def build_interpolatable_otfs(self, designspace, **kwargs):
        """Build OpenType binaries with interpolatable TrueType outlines
        from DesignSpaceDocument object.
        """
        return self._build_interpolatable_masters(designspace, ttf=False, **kwargs)

    def build_variable_fonts(
        self,
        designspace: designspaceLib.DesignSpaceDocument,
        variable_fonts: str = ".*",
        output_path=None,
        output_dir=None,
        ttf=True,
        optimize_gvar=True,
        optimize_cff=CFFOptimization.SPECIALIZE,
        use_production_names=None,
        reverse_direction=True,
        ttf_curves=CurveConversion.ALL_CUBIC_TO_QUAD,
        conversion_error=None,
        feature_writers=None,
        cff_round_tolerance=None,
        debug_feature_file=None,
        fea_include_dir=None,
        flatten_components=False,
        filters=None,
        auto_use_my_metrics=True,
        drop_implied_oncurves=False,
        **kwargs,
    ):
        """Build OpenType variable fonts from masters in a designspace."""
        assert not (output_path and output_dir), "mutually exclusive args"

        vfs_in_document = designspace.getVariableFonts()
        if not vfs_in_document:
            logger.warning(
                "No variable fonts in given designspace %s", designspace.path
            )
            return {}

        vfs_to_build = []
        for vf in vfs_in_document:
            # Skip variable fonts that do not match the user's inclusion regex if given.
            if not fullmatch(variable_fonts, vf.name):
                continue
            vfs_to_build.append(vf)

        if not vfs_to_build:
            logger.warning("No variable fonts matching %s", variable_fonts)
            return {}

        if len(vfs_to_build) > 1 and output_path:
            raise FontmakeError(
                "can't specify output path because there are several VFs to build",
                designspace.path,
            )

        vf_name_to_output_path = {}
        if len(vfs_to_build) == 1 and output_path is not None:
            vf_name_to_output_path[vfs_to_build[0].name] = output_path
        else:
            for vf in vfs_to_build:
                ext = "ttf" if ttf else "otf"
                font_name = vf.name
                if vf.filename is not None:
                    font_name = Path(vf.filename).stem
                output_path = self._output_path(
                    font_name, ext, is_variable=True, output_dir=output_dir
                )
                vf_name_to_output_path[vf.name] = output_path

        logger.info(
            "Building variable fonts " + ", ".join(vf_name_to_output_path.values())
        )

        if ttf:
            ttf_curves = CurveConversion(ttf_curves)
            fonts = ufo2ft.compileVariableTTFs(
                designspace,
                featureWriters=feature_writers,
                useProductionNames=use_production_names,
                convertCubics=ttf_curves.convertCubics,
                allQuadratic=ttf_curves.allQuadratic,
                cubicConversionError=conversion_error,
                reverseDirection=reverse_direction,
                optimizeGvar=optimize_gvar,
                flattenComponents=flatten_components,
                debugFeatureFile=debug_feature_file,
                feaIncludeDir=fea_include_dir,
                filters=filters,
                inplace=True,
                variableFontNames=list(vf_name_to_output_path),
                autoUseMyMetrics=auto_use_my_metrics,
                dropImpliedOnCurves=drop_implied_oncurves,
            )
        else:
            fonts = ufo2ft.compileVariableCFF2s(
                designspace,
                featureWriters=feature_writers,
                useProductionNames=use_production_names,
                roundTolerance=cff_round_tolerance,
                debugFeatureFile=debug_feature_file,
                feaIncludeDir=fea_include_dir,
                optimizeCFF=optimize_cff,
                filters=filters,
                inplace=True,
                variableFontNames=list(vf_name_to_output_path),
            )

        for name, font in fonts.items():
            output_path = vf_name_to_output_path[name]
            logger.info("Saving %s", output_path)
            font.save(_ensure_parent_dir(output_path))

    def _iter_compile(self, ufos, ttf=False, debugFeatureFile=None, **kwargs):
        # generator function that calls ufo2ft compiler for each ufo and
        # yields ttFont instances
        options = dict(kwargs)
        if ttf:
            for key in ("optimizeCFF", "roundTolerance", "subroutinizer", "cffVersion"):
                options.pop(key, None)
            compile_func, fmt = ufo2ft.compileTTF, "TTF"
        else:
            for key in (
                "convertCubics",
                "cubicConversionError",
                "allQuadratic",
                "reverseDirection",
                "flattenComponents",
                "autoUseMyMetrics",
                "dropImpliedOnCurves",
            ):
                options.pop(key, None)
            compile_func, fmt = ufo2ft.compileOTF, "OTF"

        writeFontName = len(ufos) > 1
        for ufo in ufos:
            name = self._font_name(ufo)
            logger.info(f"Building {fmt} for {name}")

            if debugFeatureFile and writeFontName:
                debugFeatureFile.write(f"\n### {name} ###\n")

            try:
                yield compile_func(ufo, debugFeatureFile=debugFeatureFile, **options)
            except Exception as e:
                raise FontmakeError("Compiling UFO failed", ufo.path) from e

    @timer()
    def save_otfs(
        self,
        ufos,
        ttf=False,
        is_instance=False,
        autohint=None,
        subset=None,
        use_production_names=None,
        subroutinize=None,  # deprecated
        optimize_cff=CFFOptimization.NONE,
        cff_round_tolerance=None,
        remove_overlaps=True,
        overlaps_backend=None,
        reverse_direction=True,
        ttf_curves=CurveConversion.ALL_CUBIC_TO_QUAD,
        conversion_error=None,
        feature_writers=None,
        interpolate_layout_from=None,
        interpolate_layout_dir=None,
        output_path=None,
        output_dir=None,
        debug_feature_file=None,
        inplace=True,
        cff_version=1,
        subroutinizer=None,
        flatten_components=False,
        filters=None,
        generate_GDEF=True,
        fea_include_dir=None,
        auto_use_my_metrics=True,
        drop_implied_oncurves=False,
    ):
        """Build OpenType binaries from UFOs.

        Args:
            ufos: Font objects to compile.
            ttf: If True, build fonts with TrueType outlines and .ttf extension.
            is_instance: If output fonts are instances, for generating paths.
            autohint (Union[bool, None, str]): Parameters to provide to ttfautohint.
                If set to None (default), the UFO lib is scanned for autohinting parameters.
                If nothing is found, the autohinting step is skipped. The lib key is
                "com.schriftgestaltung.customParameter.InstanceDescriptorAsGSInstance.TTFAutohint options".
                If set to False, then no autohinting takes place whether or not the
                source specifies 'TTFAutohint options'. If True, it runs ttfautohint
                with no additional options.
            subset: Whether to subset the output according to data in the UFOs.
                If not provided, also determined by flags in the UFOs.
            use_production_names: Whether to use production glyph names in the
                output. If not provided, determined by flags in the UFOs.
            subroutinize: If True, subroutinize CFF outlines in output.
            cff_round_tolerance (float): controls the rounding of point
                coordinates in CFF table. It is defined as the maximum absolute
                difference between the original float and the rounded integer
                value. By default, all floats are rounded to integer (tolerance
                0.5); a value of 0 completely disables rounding; values in
                between only round floats which are close to their integral
                part within the tolerated range. Ignored if ttf=True.
            remove_overlaps: If True, remove overlaps in glyph shapes.
            overlaps_backend: name of the library to remove overlaps. Can be
                either "booleanOperations" (default) or "pathops".
            reverse_direction: If True, reverse contour directions when
                compiling TrueType outlines.
            ttf_curves: Choose between "cu2qu" (default), "mixed", "keep-quad" or
                "keep-cubic". NOTE: cubics in TTF use glyf v1 which is still draft!
            conversion_error: Error to allow when converting cubic CFF contours
                to quadratic TrueType contours.
            feature_writers: list of ufo2ft-compatible feature writer classes
                or pre-initialized objects that are passed on to ufo2ft
                feature compiler to generate automatic feature code. The
                default value (None) means that ufo2ft will use its built-in
                default feature writers (for kern, mark, mkmk, etc.). An empty
                list ([]) will skip any automatic feature generation.
            interpolate_layout_from: A DesignSpaceDocument object to give varLib
                for interpolating layout tables to use in output.
            interpolate_layout_dir: Directory containing the compiled master
                fonts to use for interpolating binary layout tables.
            output_path: output font file path. Only works when the input
                'ufos' list contains a single font.
            output_dir: directory where to save output files. Mutually
                exclusive with 'output_path' argument.
            flatten_components: If True, flatten nested components to a single
                level.
            filters: list of ufo2ft-compatible filter classes or
                pre-initialized objects that are passed on to ufo2ft
                pre-processor to modify the glyph set. The filters are either
                pre-filters or post-filters, called before or after the default
                filters. The default filters are format specific and some can
                be disabled with other arguments.
            auto_use_my_metrics: whether to automatically set USE_MY_METRICS glyf
                component flags (0x0200). Not needed unless the font has hinted metrics.
            drop_implied_oncurves: drop on-curve points that can be implied when exactly
                in the middle of two off-curve points (TrueType only; default: False).
        """  # noqa: B950
        assert not (output_path and output_dir), "mutually exclusive args"

        if output_path is not None and len(ufos) > 1:
            raise ValueError("output_path requires a single input")

        ttf_curves = CurveConversion(ttf_curves)

        if subroutinize is not None:
            import warnings

            warnings.warn(
                "the 'subroutinize' argument is deprecated, use 'optimize_cff'",
                UserWarning,
                stacklevel=2,
            )
            if subroutinize:
                optimize_cff = CFFOptimization.SUBROUTINIZE
            else:
                # for b/w compatibility, we still run the charstring specializer
                # even when --no-subroutinize is used. Use the new --optimize-cff
                # option to disable both specilization and subroutinization
                optimize_cff = CFFOptimization.SPECIALIZE

        ext = "ttf" if ttf else "otf"

        if interpolate_layout_from is not None:
            if interpolate_layout_dir is None:
                interpolate_layout_dir = self._output_dir(ext, is_instance=False)
            finder = partial(_varLib_finder, directory=interpolate_layout_dir, ext=ext)
            # no need to generate automatic features in ufo2ft, since here we
            # are interpolating precompiled GPOS table with fontTools.varLib.
            # An empty 'featureWriters' list tells ufo2ft to not generate any
            # automatic features.
            # TODO: Add an argument to ufo2ft.compileOTF/compileTTF to
            # completely skip compiling features into OTL tables
            feature_writers = []

        fonts = self._iter_compile(
            ufos,
            ttf,
            removeOverlaps=remove_overlaps,
            overlapsBackend=overlaps_backend,
            optimizeCFF=optimize_cff,
            roundTolerance=cff_round_tolerance,
            useProductionNames=use_production_names,
            reverseDirection=reverse_direction,
            convertCubics=ttf_curves.convertCubics,
            allQuadratic=ttf_curves.allQuadratic,
            cubicConversionError=conversion_error,
            featureWriters=feature_writers,
            debugFeatureFile=debug_feature_file,
            feaIncludeDir=fea_include_dir,
            cffVersion=cff_version,
            subroutinizer=subroutinizer,
            flattenComponents=flatten_components,
            filters=filters,
            autoUseMyMetrics=auto_use_my_metrics,
            dropImpliedOnCurves=drop_implied_oncurves,
            inplace=True,  # avoid extra copy
        )

        if interpolate_layout_from is not None:
            master_locations = self._designspace_full_source_locations(
                interpolate_layout_from
            )
        for font, ufo in zip(fonts, ufos):
            if (
                interpolate_layout_from is not None
                and INSTANCE_LOCATION_KEY in ufo.tempLib
            ):
                loc = ufo.tempLib[INSTANCE_LOCATION_KEY]
                gpos_src = interpolate_layout(
                    interpolate_layout_from, loc, finder, mapped=True
                )
                font["GPOS"] = gpos_src["GPOS"]
                gsub_src = TTFont(finder(self._closest_location(master_locations, loc)))
                if "GDEF" in gsub_src:
                    font["GDEF"] = gsub_src["GDEF"]
                if "GSUB" in gsub_src:
                    font["GSUB"] = gsub_src["GSUB"]

            # Decide on autohinting and its parameters
            autohint_thisfont = (
                (
                    None
                    if autohint is False
                    else ""  # use default options if autohint=True
                    if autohint is True
                    else autohint
                    if autohint is not None
                    else ufo.lib.get(AUTOHINTING_PARAMETERS)
                )
                if ttf
                else None
            )

            if autohint_thisfont is not None:
                # if we are autohinting, we save the unhinted font to a
                # temporary path, and the hinted one to the final destination
                fd, otf_path = tempfile.mkstemp("." + ext)
                os.close(fd)
            elif output_path is None:
                otf_path = self._output_path(
                    ufo, ext, is_instance, output_dir=output_dir
                )
            else:
                otf_path = output_path

            logger.info("Saving %s", otf_path)
            font.save(_ensure_parent_dir(otf_path))

            # 'subset' is an Optional[bool], can be None, True or False.
            # When False, we never subset; when True, we always do; when
            # None (default), we check the presence of custom parameters
            if subset is False:
                pass
            elif subset is True or needs_subsetting(ufo):
                self.subset_otf_from_ufo(otf_path, ufo)

            if autohint_thisfont is None:
                continue

            if output_path is not None:
                hinted_otf_path = output_path
            else:
                hinted_otf_path = self._output_path(
                    ufo, ext, is_instance, autohinted=True, output_dir=output_dir
                )
            try:
                logger.info("Autohinting %s", hinted_otf_path)
                ttfautohint(
                    otf_path,
                    _ensure_parent_dir(hinted_otf_path),
                    args=autohint_thisfont,
                )
            except TTFAError:
                # copy unhinted font to destination before re-raising error
                shutil.copyfile(otf_path, hinted_otf_path)
                raise
            finally:
                # must clean up temp file
                os.remove(otf_path)

    def _save_interpolatable_fonts(self, designspace, output_dir, ttf):
        ext = "ttf" if ttf else "otf"
        for source in designspace.sources:
            assert isinstance(source.font, TTFont)
            otf_path = self._output_path(
                source,
                ext,
                is_instance=False,
                interpolatable=True,
                output_dir=output_dir,
                suffix=source.layerName,
            )
            logger.info("Saving %s", otf_path)
            source.font.save(_ensure_parent_dir(otf_path))
            source.path = otf_path
            source.layerName = None
        for instance in designspace.instances:
            instance.path = instance.filename = None

        if output_dir is None:
            output_dir = self._output_dir(ext, interpolatable=True)
        designspace_path = os.path.join(output_dir, os.path.basename(designspace.path))
        logger.info("Saving %s", designspace_path)
        designspace.write(designspace_path)

    def subset_otf_from_ufo(self, otf_path, ufo):
        """Subset a font using "Keep Glyphs"/"Remove Glyphs" custom parameters,
        and export flags as set by glyphsLib.

        "Export Glyphs" is currently not supported:
        https://github.com/googlei18n/glyphsLib/issues/295.
        """
        from fontTools import subset

        # we must exclude from the final UFO glyphOrder all the glyphs that were not
        # exported to OTF because included in 'public.skipExportGlyphs'
        skip_export_glyphs = set(ufo.lib.get("public.skipExportGlyphs", ()))
        exported_glyphs = dict.fromkeys(
            g for g in ufo.keys() if g not in skip_export_glyphs
        )
        ufo_order = makeOfficialGlyphOrder(exported_glyphs, glyphOrder=ufo.glyphOrder)
        # ufo2ft always inserts a ".notdef" glyph as the first glyph
        if ".notdef" not in exported_glyphs:
            ufo_order.insert(0, ".notdef")
        ot_order = TTFont(otf_path).getGlyphOrder()
        assert ot_order[0] == ".notdef"
        assert len(ufo_order) == len(ot_order)

        for key in (KEEP_GLYPHS_NEW_KEY, KEEP_GLYPHS_OLD_KEY):
            keep_glyphs_list = ufo.lib.get(key)
            if keep_glyphs_list is not None:
                keep_glyphs = set(keep_glyphs_list)
                break
        else:
            keep_glyphs = None

        for key in (REMOVE_GLYPHS_NEW_KEY, REMOVE_GLYPHS_OLD_KEY):
            remove_glyphs_list = ufo.lib.get(key)
            if remove_glyphs_list is not None:
                remove_glyphs = set(remove_glyphs_list)
                break
        else:
            remove_glyphs = None

        include = []
        for source_name, binary_name in zip(ufo_order, ot_order):
            if keep_glyphs and source_name not in keep_glyphs:
                continue

            if remove_glyphs and source_name in remove_glyphs:
                continue

            if source_name in ufo:
                exported = ufo[source_name].lib.get(GLYPH_EXPORT_KEY, True)
                if not exported:
                    continue

            include.append(binary_name)

        # copied from nototools.subset
        opt = subset.Options()
        opt.name_IDs = ["*"]
        opt.name_legacy = True
        opt.name_languages = ["*"]
        opt.layout_features = ["*"]
        opt.notdef_outline = True
        opt.recalc_bounds = True
        opt.recalc_timestamp = True
        opt.canonical_order = True

        opt.glyph_names = True

        font = subset.load_font(otf_path, opt, lazy=False)
        subsetter = subset.Subsetter(options=opt)
        subsetter.populate(glyphs=include)
        subsetter.subset(font)
        subset.save_font(font, otf_path, opt)

    def run_from_glyphs(
        self,
        glyphs_path,
        designspace_path=None,
        master_dir=None,
        instance_dir=None,
        family_name=None,
        mti_source=None,
        write_skipexportglyphs=True,
        generate_GDEF=True,
        glyph_data=None,
        output=(),
        output_dir=None,
        interpolate=False,
        **kwargs,
    ):
        """Run toolchain from Glyphs source.

        Args:
            glyphs_path: Path to source file.
            designspace_path: Output path of generated designspace document.
                By default it's "<family_name>[-<base_style>].designspace".
            master_dir: Directory where to save UFO masters (default:
                "master_ufo").
            instance_dir: Directory where to save UFO instances (default:
                "instance_ufo").
            family_name: If provided, uses this family name in the output.
            mti_source: Path to property list file containing a dictionary
                mapping UFO masters to dictionaries mapping layout table
                tags to MTI source paths which should be compiled into
                those tables.
            glyph_data: A list of GlyphData XML file paths.
            kwargs: Arguments passed along to run_from_designspace.
        """
        # only save *master* UFOs when explicitly requested: i.e. outputs contain
        # 'ufo' and the -i/--interpolate option was not passed (that's for *instances*)
        # or a --master-dir was set
        save_ufos = "ufo" in output and (not interpolate or master_dir is not None)
        # take --output-dir to mean same as --master-dir when -o ufo and not -i
        if (
            set(output) == {"ufo"}
            and not interpolate
            and master_dir is None
            and output_dir is not None
        ):
            master_dir = output_dir

        logger.info("Building master UFOs and designspace from Glyphs source")
        designspace = self.build_master_ufos(
            glyphs_path,
            designspace_path=designspace_path,
            master_dir=master_dir,
            instance_dir=instance_dir,
            family_name=family_name,
            mti_source=mti_source,
            write_skipexportglyphs=write_skipexportglyphs,
            generate_GDEF=generate_GDEF,
            ufo_structure=kwargs.get("ufo_structure", "package"),
            indent_json=kwargs.get("indent_json"),
            glyph_data=glyph_data,
            save_ufos=save_ufos,
        )
        # 'include' statements in features.fea should be resolved relative to
        # the input .glyphs path, like Glyphs.app would do, and not relative
        # to the UFOs that are generated by glyphsLib.
        fea_include_dir = os.path.dirname(glyphs_path)
        try:
            self.run_from_designspace(
                designspace,
                output=output,
                fea_include_dir=fea_include_dir,
                output_dir=output_dir,
                interpolate=interpolate,
                **kwargs,
            )
        except FontmakeError as e:
            e.source_trail.append(glyphs_path)
            raise

    def _instance_ufo_path(
        self, instance, designspace_path, output_dir=None, ufo_structure="package"
    ):
        """Return an instance path, optionally overriding output dir or extension"""
        # prefer absolute instance.path over relative instance.filename
        instance_path = instance.path
        if instance_path is not None:
            instance_dir = Path(instance_path).parent
        elif instance.filename is not None:
            instance_path = Path(designspace_path).parent / instance.filename
            instance_dir = instance_path.parent
        else:
            # if neither is set, make one up from UFO family/style names
            instance_path = self._font_name(instance.font)
            instance_dir = None

        # let --output-dir override the instance UFO directory
        if output_dir is not None:
            instance_dir = output_dir

        # fall back to 'instance_ufo/' if we can't find a suitable directory
        if instance_dir is None:
            instance_dir = self._output_dir("ufo", is_instance=True)

        instance_path = Path(instance_dir) / Path(instance_path).name
        return self._fix_ufo_path(instance_path, ufo_structure)

    def interpolate_instance_ufos(
        self,
        designspace,
        include=None,
        round_instances=False,
        expand_features_to_instances=False,
        fea_include_dir=None,
        ufo_structure="package",
        indent_json=False,
        save_ufos=True,
        output_path=None,
        output_dir=None,
    ):
        """Interpolate master UFOs with Instantiator and return instance UFOs.

        Args:
            designspace: a DesignSpaceDocument object containing sources and
                instances.
            include (str): optional regular expression pattern to match the
                DS instance 'name' attribute and only interpolate the matching
                instances.
            round_instances (bool): round instances' coordinates to integer.
            expand_features_to_instances: parses the master feature file, expands all
                include()s and writes the resulting full feature file to all instance
                UFOs. Use this if you share feature files among masters in external
                files. Otherwise, the relative include paths can break as instances
                may end up elsewhere. Only done on interpolation.
        Returns:
            generator of ufoLib2.Font objects corresponding to the UFO instances.
        Raises:
            FontmakeError: instances could not be prepared for interpolation or
                interpolation failed.
            ValueError: an instance descriptor did not have a filename attribute set.
        """
        from glyphsLib.interpolation import apply_instance_data_to_ufo

        assert not (output_path and output_dir), "mutually exclusive args"

        logger.info("Interpolating master UFOs from designspace")
        for _location, subDoc in splitInterpolable(designspace):
            try:
                generator = instantiator.Instantiator.from_designspace(
                    subDoc, round_geometry=round_instances
                )
            except instantiator.InstantiatorError as e:
                raise FontmakeError(
                    "Preparing the Designspace for interpolation failed",
                    designspace.path,
                ) from e

            if expand_features_to_instances:
                logger.debug("Expanding features to instance UFOs")
                fea_txt = parseLayoutFeatures(
                    subDoc.default.font, includeDir=fea_include_dir
                ).asFea()
                generator = attr.evolve(generator, copy_feature_text=fea_txt)

            for instance in subDoc.instances:
                # Skip instances that have been set to non-export in Glyphs, stored as the
                # instance's `com.schriftgestaltung.export` lib key.
                if not instance.lib.get("com.schriftgestaltung.export", True):
                    continue

                # Skip instances that do not match the user's inclusion regex if given.
                if include is not None and not fullmatch(include, instance.name):
                    continue

                logger.info("Generating instance UFO for {!r}".format(instance.name))

                try:
                    instance.font = generator.generate_instance(instance)
                except instantiator.InstantiatorError as e:
                    raise FontmakeError(
                        "Interpolating instance {!r} failed.".format(
                            instance.styleName
                        ),
                        designspace.path,
                    ) from e

                apply_instance_data_to_ufo(instance.font, instance, subDoc)

                if save_ufos:
                    if output_path is not None:
                        # we don't know in advance how many instances we will generate
                        # (depends on splitInterpolable and include filter); if we
                        # overwrite or stop in the middle of the build it'd be worse,
                        # so we make the output_path unique using #1, #2, etc. suffix
                        instance_path = makeOutputFileName(
                            output_path,
                            extension=UFO_STRUCTURE_EXTENSIONS[ufo_structure],
                        )
                    else:
                        instance_path = self._instance_ufo_path(
                            instance, designspace.path, output_dir, ufo_structure
                        )
                    logger.info("Saving %s", instance_path)
                    self.save_ufo_as(
                        instance.font, instance_path, ufo_structure, indent_json
                    )
                elif instance.filename is not None:
                    # saving a UFO sets its path attribute; when saving the binary font
                    # compiled from this UFO, self._output_path() uses the ufo.path to
                    # make up the output path. Since we aren't saving the UFO in this
                    # case, the ufo.path is not set (it's a read-only attribute).
                    # Therefore we resort to this temporary lib key to pass down the DS
                    # instance filename to self._output_path() method and make sure the
                    # font is named correctly whether or not the UFO is saved to disk.
                    instance.font.tempLib[INSTANCE_FILENAME_KEY] = instance.filename

                # --interpolate-binary-layout needs to know the location of each
                # instance UFO; the previous code relied on matching instance.path and
                # ufo.path, but we no longer necessarily save the UFO thus the ufo.path
                # may not be set. Instead store the location directly in the ufo.tempLib
                instance.font.tempLib[INSTANCE_LOCATION_KEY] = instance.location

                yield instance.font

    def run_from_designspace(
        self,
        designspace,
        output=(),
        interpolate=False,
        variable_fonts: str = ".*",
        masters_as_instances=False,
        interpolate_binary_layout=False,
        round_instances=False,
        feature_writers=None,
        filters=None,
        expand_features_to_instances=False,
        check_compatibility=None,
        **kwargs,
    ):
        """Run toolchain from a DesignSpace document to produce either static
        instance fonts (ttf or otf), interpolatable or variable fonts.

        Args:
            designspace: Path to designspace or DesignSpaceDocument object.
            interpolate: If True output all instance fonts, otherwise just
                masters. If the value is a string, only build instance(s) that
                match given name. The string is compiled into a regular
                expression and matched against the "name" attribute of
                designspace instances using `re.fullmatch`.
            variable_fonts: if True output all variable fonts, otherwise if the
                value is a string, only build variable fonts that match the
                given filename. As above, the string is compiled into a regular
                expression and matched against the "filename" attribute of
                designspace variable fonts using `re.fullmatch`.
            masters_as_instances: If True, output master fonts as instances.
            interpolate_binary_layout: Interpolate layout tables from compiled
                master binaries.
            round_instances: apply integer rounding when interpolating static
                instance UFOs.
            kwargs: Arguments passed along to run_from_ufos.

        Raises:
            TypeError: "variable" or "interpolatable" outputs are incompatible
                with arguments "interpolate", "masters_as_instances", and
                "interpolate_binary_layout".
        """

        interp_outputs = INTERPOLATABLE_OUTPUTS.intersection(output)
        static_outputs = set(output).difference(interp_outputs)
        if interp_outputs:
            for argname in (
                "interpolate",
                "masters_as_instances",
                "interpolate_binary_layout",
            ):
                if locals()[argname]:
                    raise TypeError(
                        '"%s" argument incompatible with output %r'
                        % (argname, ", ".join(sorted(interp_outputs)))
                    )

        if isinstance(designspace, (str, os.PathLike)):
            designspace_path = os.fspath(designspace)
            try:
                designspace = designspaceLib.DesignSpaceDocument.fromfile(
                    designspace_path
                )
            except Exception as e:
                raise FontmakeError(
                    "Reading Designspace failed", designspace_path
                ) from e
        elif isinstance(designspace, designspaceLib.DesignSpaceDocument):
            # get our own DS copy so we can modify in-place
            designspace = designspace.deepcopyExceptFonts()
        else:
            raise TypeError(
                f"expected path or DesignSpaceDocument, found {type(designspace.__name__)}"
            )

        logger.info("Loading %s DesignSpace source UFOs", len(designspace.sources))
        designspace.loadSourceFonts(opener=self.open_ufo)

        # if no --feature-writers option was passed, check in the designspace's
        # <lib> element if user supplied a custom featureWriters configuration;
        # if so, use that for all the UFOs built from this designspace
        if feature_writers is None and FEATURE_WRITERS_KEY in designspace.lib:
            feature_writers = loadFeatureWriters(designspace)

        if filters is None and FILTERS_KEY in designspace.lib:
            preFilters, postFilters = loadFilters(designspace)
            filters = preFilters + postFilters

        # Since Designspace version 5, one designspace file can have discrete
        # axes (that do not interpolate) and thus only some sub-spaces are
        # actually compatible for interpolation.
        for discrete_location, subDoc in splitInterpolable(designspace):
            # glyphsLib currently stores this custom parameter on the fonts,
            # not the designspace, so we check if it exists in any font's lib.
            source_fonts = [source.font for source in subDoc.sources]
            explicit_check = any(
                font.lib.get(COMPAT_CHECK_KEY, False) for font in source_fonts
            )
            if check_compatibility is not False and (
                interp_outputs or check_compatibility or explicit_check
            ):
                if not CompatibilityChecker(source_fonts).check():
                    message = "Compatibility check failed"
                    if discrete_location:
                        message += f" in interpolable sub-space at {discrete_location}"
                    raise FontmakeError(message, designspace.path)

        try:
            if static_outputs:
                self._run_from_designspace_static(
                    designspace,
                    outputs=static_outputs,
                    interpolate=interpolate,
                    masters_as_instances=masters_as_instances,
                    interpolate_binary_layout=interpolate_binary_layout,
                    round_instances=round_instances,
                    feature_writers=feature_writers,
                    expand_features_to_instances=expand_features_to_instances,
                    filters=filters,
                    **kwargs,
                )
            if interp_outputs:
                self._run_from_designspace_interpolatable(
                    designspace,
                    outputs=interp_outputs,
                    variable_fonts=variable_fonts,
                    feature_writers=feature_writers,
                    filters=filters,
                    **kwargs,
                )
        except FontmakeError as e:
            # Some called functions already added the Designspace file to the source
            # trail.
            if e.source_trail[-1] != designspace.path:
                e.source_trail.append(designspace.path)
            raise
        except Exception as e:
            raise FontmakeError(
                "Generating fonts from Designspace failed", designspace.path
            ) from e

    def _run_from_designspace_static(
        self,
        designspace,
        outputs,
        interpolate=False,
        masters_as_instances=False,
        interpolate_binary_layout=False,
        round_instances=False,
        feature_writers=None,
        expand_features_to_instances=False,
        fea_include_dir=None,
        ufo_structure="package",
        indent_json=False,
        output_path=None,
        output_dir=None,
        **kwargs,
    ):
        save_ufos = "ufo" in outputs
        ufos = []
        if not interpolate or masters_as_instances:
            unique_srcs = {id(s.font): s.font for s in designspace.sources}
            ufos.extend(unique_srcs.values())
        if interpolate:
            pattern = interpolate if isinstance(interpolate, str) else None
            # use --output-{path,dir} options for instance UFOs if 'ufo' is the only -o
            ufo_output_path = ufo_output_dir = None
            if set(outputs) == {"ufo"}:
                if output_path is not None:
                    ufo_output_path = output_path
                if output_dir is not None:
                    ufo_output_dir = output_dir
            ufos.extend(
                self.interpolate_instance_ufos(
                    designspace,
                    include=pattern,
                    round_instances=round_instances,
                    expand_features_to_instances=expand_features_to_instances,
                    fea_include_dir=fea_include_dir,
                    ufo_structure=ufo_structure,
                    indent_json=indent_json,
                    save_ufos=save_ufos,
                    output_path=ufo_output_path,
                    output_dir=ufo_output_dir,
                )
            )

        if interpolate_binary_layout is False:
            interpolate_layout_from = interpolate_layout_dir = None
        else:
            interpolate_layout_from = designspace
            # Unload UFO fonts, we will reload them as binary
            for s in interpolate_layout_from.sources:
                s.font = None
            if isinstance(interpolate_binary_layout, str):
                interpolate_layout_dir = interpolate_binary_layout
            else:
                interpolate_layout_dir = None

        self.run_from_ufos(
            ufos,
            output=outputs,
            is_instance=(interpolate or masters_as_instances),
            interpolate_layout_from=interpolate_layout_from,
            interpolate_layout_dir=interpolate_layout_dir,
            feature_writers=feature_writers,
            fea_include_dir=fea_include_dir,
            output_path=output_path,
            output_dir=output_dir,
            **kwargs,
        )

    def _run_from_designspace_interpolatable(
        self,
        designspace,
        outputs,
        variable_fonts: str = ".*",
        output_path=None,
        output_dir=None,
        **kwargs,
    ):
        ttf_designspace = otf_designspace = None

        if "variable" in outputs:
            self.build_variable_fonts(
                designspace,
                variable_fonts=variable_fonts,
                output_path=output_path,
                output_dir=output_dir,
                **kwargs,
            )

        if "ttf-interpolatable" in outputs:
            ttf_designspace = self.build_interpolatable_ttfs(designspace, **kwargs)
            self._save_interpolatable_fonts(ttf_designspace, output_dir, ttf=True)

        if "variable-cff2" in outputs:
            self.build_variable_fonts(
                designspace,
                variable_fonts=variable_fonts,
                output_path=output_path,
                output_dir=output_dir,
                ttf=False,
                **kwargs,
            )

        if "otf-interpolatable" in outputs:
            otf_designspace = self.build_interpolatable_otfs(designspace, **kwargs)
            self._save_interpolatable_fonts(otf_designspace, output_dir, ttf=False)

    def run_from_ufos(self, ufos, output=(), **kwargs):
        """Run toolchain from UFO sources.

        Args:
            ufos: List of UFO sources, as either paths or opened objects.
            output: List of output formats to generate.
            kwargs: Arguments passed along to save_otfs.
        """

        if set(output) == {"ufo"}:
            return

        if "otf" in output and "otf-cff2" in output:
            raise ValueError("'otf' and 'otf-cff2' outputs are mutually exclusive")

        # the `ufos` parameter can be a list of UFO objects
        # or it can be a path (string) with a glob syntax
        if isinstance(ufos, str):
            ufos = [self.open_ufo(x) for x in glob.glob(ufos)]
        elif isinstance(ufos, list):
            # ufos can be either paths or open Font objects, so normalize them
            ufos = [self.open_ufo(x) if isinstance(x, str) else x for x in ufos]
        else:
            raise TypeError(
                "UFOs parameter is neither a ufoLib2.Font object, a path or a glob, "
                f"nor a list of any of these: {ufos:r}."
            )

        cff_version = 1 if "otf" in output else 2 if "otf-cff2" in output else None

        # if building both OTF & TTF we must tell ufo2ft to compile with inplace=False
        inplace = not (cff_version is not None and "ttf" in output)

        if cff_version is not None:
            self.build_otfs(ufos, cff_version=cff_version, inplace=inplace, **kwargs)

        if "ttf" in output:
            self.build_ttfs(ufos, inplace=inplace, **kwargs)

    @staticmethod
    def _search_instances(designspace, pattern):
        instances = OrderedDict()
        for instance in designspace.instances:
            # is 'name' optional? 'filename' certainly must not be
            if fullmatch(pattern, instance.name):
                instances[instance.name] = instance.filename
        if not instances:
            raise FontmakeError("No instance found with %r" % pattern)
        return instances

    def _font_name(self, ufo):
        """Generate a postscript-style font name."""
        family_name = (
            ufo.info.familyName.replace(" ", "")
            if ufo.info.familyName is not None
            else "None"
        )
        style_name = (
            ufo.info.styleName.replace(" ", "")
            if ufo.info.styleName is not None
            else "None"
        )
        return f"{family_name}-{style_name}"

    def _output_dir(
        self,
        ext,
        is_instance=False,
        interpolatable=False,
        autohinted=False,
        is_variable=False,
    ):
        """Generate an output directory.

        Args:
            ext: extension string.
            is_instance: The output is instance font or not.
            interpolatable: The output is interpolatable or not.
            autohinted: The output is autohinted or not.
            is_variable: The output is variable font or not.
        Return:
            output directory string.
        """

        assert not (is_variable and any([is_instance, interpolatable]))
        # FIXME? Use user configurable destination folders.
        if is_variable:
            dir_prefix = "variable_"
        elif is_instance:
            dir_prefix = "instance_"
        else:
            dir_prefix = "master_"
        dir_suffix = "_interpolatable" if interpolatable else ""
        output_dir = dir_prefix + ext + dir_suffix
        if autohinted:
            output_dir = os.path.join("autohinted", output_dir)
        return output_dir

    def _output_path(
        self,
        ufo_or_font_name,
        ext,
        is_instance=False,
        interpolatable=False,
        autohinted=False,
        is_variable=False,
        output_dir=None,
        suffix=None,
    ):
        """Generate output path for a font file with given extension."""

        if isinstance(ufo_or_font_name, str):
            font_name = ufo_or_font_name
        else:
            ufo = ufo_or_font_name
            if ufo.path:
                font_name = os.path.splitext(
                    os.path.basename(os.path.normpath(ufo.path))
                )[0]
            elif INSTANCE_FILENAME_KEY in ufo.tempLib:
                font_name = Path(ufo.tempLib[INSTANCE_FILENAME_KEY]).stem
            else:
                font_name = self._font_name(ufo)

        if output_dir is None:
            output_dir = self._output_dir(
                ext, is_instance, interpolatable, autohinted, is_variable
            )

        if suffix:
            return os.path.join(output_dir, f"{font_name}-{suffix}.{ext}")
        else:
            return os.path.join(output_dir, f"{font_name}.{ext}")

    def _designspace_full_source_locations(self, designspace):
        """Map "full" sources' paths to their locations in a designspace.

        'Sparse layer' sources only contributing glyph outlines but no
        info/kerning/features are ignored.
        """
        location_map = {}
        default_source = designspace.findDefault()
        for source in designspace.sources:
            if source is default_source or source.layerName is not None:
                location_map[_normpath(source.path)] = source.location
        return location_map

    def _closest_location(self, location_map, target):
        """Return path of font whose location is closest to target."""

        def dist(a, b):
            return math.sqrt(sum((a[k] - b[k]) ** 2 for k in a.keys()))

        paths = iter(location_map.keys())
        closest = next(paths)
        closest_dist = dist(target, location_map[closest])
        for path in paths:
            cur_dist = dist(target, location_map[path])
            if cur_dist < closest_dist:
                closest = path
                closest_dist = cur_dist
        return closest


def _varLib_finder(source, directory="", ext="ttf"):
    """Finder function to be used with varLib.build to find master TTFs given
    the filename of the source UFO master as specified in the designspace.
    It replaces the UFO directory with the one specified in 'directory'
    argument, and replaces the file extension with 'ext'.
    """
    fname = os.path.splitext(os.path.basename(source))[0] + "." + ext
    return os.path.join(directory, fname)


def _normpath(fname):
    return os.path.normcase(os.path.normpath(fname))


def _ensure_parent_dir(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    return path
