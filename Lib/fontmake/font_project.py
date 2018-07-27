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


from __future__ import print_function, division, absolute_import
from __future__ import unicode_literals

import glob
import logging
import math
import os
from functools import partial, wraps
import tempfile
import shutil
from collections import OrderedDict
try:
    from plistlib import load as readPlist  # PY3
except ImportError:
    from plistlib import readPlist  # PY2

try:
    from re import fullmatch
except ImportError:
    import re

    def fullmatch(regex, string, flags=0):
        """Backport of python3.4 re.fullmatch()."""
        return re.match("(?:" + regex + r")\Z", string, flags=flags)

from defcon import Font
from fontTools.misc.py23 import tobytes, basestring, zip
from fontTools.misc.loggingTools import configLogger, Timer
from fontTools.misc.transform import Transform
from fontTools.pens.transformPen import TransformPen
from fontTools.pens.reverseContourPen import ReverseContourPen
from fontTools.ttLib import TTFont
from fontTools import varLib
from fontTools import designspaceLib
from fontTools.varLib.interpolate_layout import interpolate_layout
from ufo2ft import compileOTF, compileTTF, compileInterpolatableTTFs
from ufo2ft.featureCompiler import FeatureCompiler
from ufo2ft.util import makeOfficialGlyphOrder

from fontmake.errors import FontmakeError, TTFAError
from fontmake.ttfautohint import ttfautohint

logger = logging.getLogger(__name__)
timer = Timer(logging.getLogger('fontmake.timer'), level=logging.DEBUG)

PUBLIC_PREFIX = 'public.'
GLYPHS_PREFIX = 'com.schriftgestaltung.'
# for glyphsLib < 2.3.0
KEEP_GLYPHS_OLD_KEY = GLYPHS_PREFIX + "Keep Glyphs"
# for glyphsLib >= 2.3.0
KEEP_GLYPHS_NEW_KEY = (
    GLYPHS_PREFIX
    + "customParameter.InstanceDescriptorAsGSInstance.Keep Glyphs"
)
GLYPH_EXPORT_KEY = GLYPHS_PREFIX + "Glyphs.Export"


def _deprecated(func):
    import warnings

    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            "'%s' is deprecated and will be dropped in future versions"
            % func.__name__,
            category=UserWarning,
            stacklevel=2,
        )
        return func(*args, **kwargs)

    return wrapper


class FontProject(object):
    """Provides methods for building fonts."""

    def __init__(self, timing=False, verbose='INFO'):
        logging.basicConfig(level=getattr(logging, verbose.upper()))
        logging.getLogger('fontTools.subset').setLevel(logging.WARNING)
        if timing:
            configLogger(logger=timer.logger, level=logging.DEBUG)

    @timer()
    def build_master_ufos(self, glyphs_path, designspace_path=None,
                          master_dir=None, instance_dir=None,
                          family_name=None, mti_source=None):
        """Build UFOs and MutatorMath designspace from Glyphs source."""
        import glyphsLib

        if master_dir is None:
            master_dir = self._output_dir('ufo')
        if instance_dir is None:
            instance_dir = self._output_dir('ufo', is_instance=True)

        font = glyphsLib.GSFont(glyphs_path)

        if designspace_path is not None:
            designspace_dir = os.path.dirname(designspace_path)
        else:
            designspace_dir = master_dir
        # glyphsLib.to_designspace expects instance_dir to be relative
        instance_dir = os.path.relpath(instance_dir, designspace_dir)

        designspace = glyphsLib.to_designspace(
            font, family_name=family_name, instance_dir=instance_dir)

        masters = []
        for source in designspace.sources:
            masters.append(source.font)
            ufo_path = os.path.join(master_dir, source.filename)
            # no need to also set the relative 'filename' attribute as that
            # will be auto-updated on writing the designspace document
            source.path = ufo_path
            if not os.path.isdir(master_dir):
                os.makedirs(master_dir)
            source.font.save(ufo_path)

        if designspace_path is None:
            designspace_path = os.path.join(master_dir, designspace.filename)
        designspace.write(designspace_path)
        if mti_source:
            self.add_mti_features_to_master_ufos(mti_source, masters)
        return designspace_path

    @timer()
    def add_mti_features_to_master_ufos(self, mti_source, masters):
        mti_dir = os.path.dirname(mti_source)
        with open(mti_source, 'rb') as mti_file:
            mti_paths = readPlist(mti_file)
        for master in masters:
            key = os.path.basename(master.path).rstrip('.ufo')
            for table, path in mti_paths[key].items():
                with open(os.path.join(mti_dir, path), "rb") as mti_source:
                    ufo_path = (
                        'com.github.googlei18n.ufo2ft.mtiFeatures/%s.mti' %
                        table.strip())
                    master.data[ufo_path] = mti_source.read()
                # If we have MTI sources, any Adobe feature files derived from
                # the Glyphs file should be ignored. We clear it here because
                # it only contains junk information anyway.
                master.features.text = ""
            master.save()

    @_deprecated
    @timer()
    def remove_overlaps(self, ufos, glyph_filter=lambda g: len(g)):
        """Remove overlaps in UFOs' glyphs' contours."""
        from booleanOperations import union, BooleanOperationsError

        for ufo in ufos:
            font_name = self._font_name(ufo)
            logger.info('Removing overlaps for ' + font_name)
            for glyph in ufo:
                if not glyph_filter(glyph):
                    continue
                contours = list(glyph)
                glyph.clearContours()
                try:
                    union(contours, glyph.getPointPen())
                except BooleanOperationsError:
                    logger.error("Failed to remove overlaps for %s: %r",
                                 font_name, glyph.name)
                    raise

    @_deprecated
    @timer()
    def decompose_glyphs(self, ufos, glyph_filter=lambda g: True):
        """Move components of UFOs' glyphs to their outlines."""

        for ufo in ufos:
            logger.info('Decomposing glyphs for ' + self._font_name(ufo))
            for glyph in ufo:
                if not glyph.components or not glyph_filter(glyph):
                    continue
                self._deep_copy_contours(ufo, glyph, glyph, Transform())
                glyph.clearComponents()

    def _deep_copy_contours(self, ufo, parent, component, transformation):
        """Copy contours from component to parent, including nested components."""

        for nested in component.components:
            self._deep_copy_contours(
                ufo, parent, ufo[nested.baseGlyph],
                transformation.transform(nested.transformation))

        if component != parent:
            pen = TransformPen(parent.getPen(), transformation)

            # if the transformation has a negative determinant, it will reverse
            # the contour direction of the component
            xx, xy, yx, yy = transformation[:4]
            if xx*yy - xy*yx < 0:
                pen = ReverseContourPen(pen)

            component.draw(pen)

    @_deprecated
    @timer()
    def convert_curves(self, ufos, compatible=False, reverse_direction=True,
                       conversion_error=None):
        from cu2qu.ufo import font_to_quadratic, fonts_to_quadratic

        if compatible:
            logger.info('Converting curves compatibly')
            fonts_to_quadratic(
                ufos, max_err_em=conversion_error,
                reverse_direction=reverse_direction, dump_stats=True)
        else:
            for ufo in ufos:
                logger.info('Converting curves for ' + self._font_name(ufo))
                font_to_quadratic(
                    ufo, max_err_em=conversion_error,
                    reverse_direction=reverse_direction, dump_stats=True)

    def build_otfs(self, ufos, **kwargs):
        """Build OpenType binaries with CFF outlines."""
        self.save_otfs(ufos, **kwargs)

    def build_ttfs(self, ufos, **kwargs):
        """Build OpenType binaries with TrueType outlines."""
        self.save_otfs(ufos, ttf=True, **kwargs)

    def build_interpolatable_ttfs(self, ufos, **kwargs):
        """Build OpenType binaries with interpolatable TrueType outlines."""
        self.save_otfs(ufos, ttf=True, interpolatable=True, **kwargs)

    def build_variable_font(self, designspace_path, output_path=None,
                            output_dir=None, master_bin_dir=None):
        """Build OpenType variable font from masters in a designspace."""
        assert not (output_path and output_dir), "mutually exclusive args"

        if output_path is None:
            output_path = os.path.splitext(
                os.path.basename(designspace_path))[0] + '-VF'
            output_path = self._output_path(
                output_path, 'ttf', is_variable=True, output_dir=output_dir)

        logger.info('Building variable font ' + output_path)

        if master_bin_dir is None:
            master_bin_dir = self._output_dir('ttf', interpolatable=True)
        finder = partial(_varLib_finder, directory=master_bin_dir)

        font, _, _ = varLib.build(designspace_path, finder)

        font.save(output_path)

    def _iter_compile(self, ufos, ttf=False, **kwargs):
        # generator function that calls ufo2ft compiler for each ufo and
        # yields ttFont instances
        options = dict(kwargs)
        if ttf:
            for key in ("optimizeCFF", "roundTolerance"):
                options.pop(key, None)
            compile_func, fmt = compileTTF, "TTF"
        else:
            for key in ("cubicConversionError", "reverseDirection"):
                options.pop(key, None)
            compile_func, fmt = compileOTF, "OTF"

        for ufo in ufos:
            name = self._font_name(ufo)
            logger.info('Building %s for %s' % (fmt, name))

            yield compile_func(ufo, **options)

    @timer()
    def save_otfs(self,
                  ufos,
                  ttf=False,
                  is_instance=False,
                  interpolatable=False,
                  use_afdko=False,
                  autohint=None,
                  subset=None,
                  use_production_names=None,
                  subroutinize=False,
                  cff_round_tolerance=None,
                  remove_overlaps=True,
                  reverse_direction=True,
                  conversion_error=None,
                  feature_writers=None,
                  interpolate_layout_from=None,
                  interpolate_layout_dir=None,
                  output_path=None,
                  output_dir=None,
                  inplace=True):
        """Build OpenType binaries from UFOs.

        Args:
            ufos: Font objects to compile.
            ttf: If True, build fonts with TrueType outlines and .ttf extension.
            is_instance: If output fonts are instances, for generating paths.
            interpolatable: If output is interpolatable, for generating paths.
            use_afdko: If True, use AFDKO to compile feature source.
            autohint: Parameters to provide to ttfautohint. If not provided, the
                autohinting step is skipped.
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
            reverse_direction: If True, reverse contour directions when
                compiling TrueType outlines.
            conversion_error: Error to allow when converting cubic CFF contours
                to quadratic TrueType contours.
            feature_writers: list of ufo2ft-compatible feature writer classes
                or pre-initialized objects that are passed on to ufo2ft
                feature compiler to generate automatic feature code. The
                default value (None) means that ufo2ft will use its built-in
                default feature writers (for kern, mark, mkmk, etc.). An empty
                list ([]) will skip any automatic feature generation.
            interpolate_layout_from: A designspace path to give varLib for
                interpolating layout tables to use in output.
            interpolate_layout_dir: Directory containing the compiled master
                fonts to use for interpolating binary layout tables.
            output_path: output font file path. Only works when the input
                'ufos' list contains a single font.
            output_dir: directory where to save output files. Mutually
                exclusive with 'output_path' argument.
        """
        assert not (output_path and output_dir), "mutually exclusive args"

        if output_path is not None and len(ufos) > 1:
            raise ValueError("output_path requires a single input")

        ext = 'ttf' if ttf else 'otf'

        if interpolate_layout_from is not None:
            if interpolate_layout_dir is None:
                interpolate_layout_dir = self._output_dir(
                    ext, is_instance=False, interpolatable=interpolatable)
            finder = partial(_varLib_finder, directory=interpolate_layout_dir,
                             ext=ext)
            # no need to generate automatic features in ufo2ft, since here we
            # are interpolating precompiled GPOS table with fontTools.varLib.
            # An empty 'featureWriters' list tells ufo2ft to not generate any
            # automatic features.
            # TODO: Add an argument to ufo2ft.compileOTF/compileTTF to
            # completely skip compiling features into OTL tables
            feature_writers = []

        compiler_options = dict(
            useProductionNames=use_production_names,
            reverseDirection=reverse_direction,
            cubicConversionError=conversion_error,
            featureWriters=feature_writers,
            inplace=True,  # avoid extra copy
        )
        if use_afdko:
            compiler_options["featureCompilerClass"] = FDKFeatureCompiler

        if interpolatable:
            if not ttf:
                raise NotImplementedError(
                    "interpolatable CFF not supported yet")

            logger.info('Building interpolation-compatible TTFs')

            fonts = compileInterpolatableTTFs(ufos, **compiler_options)
        else:
            fonts = self._iter_compile(
                ufos,
                ttf,
                removeOverlaps=remove_overlaps,
                optimizeCFF=subroutinize,
                roundTolerance=cff_round_tolerance,
                **compiler_options)

        do_autohint = ttf and autohint is not None

        for font, ufo in zip(fonts, ufos):

            if interpolate_layout_from is not None:
                master_locations, instance_locations = self._designspace_locations(
                    interpolate_layout_from)
                loc = instance_locations[_normpath(ufo.path)]
                gpos_src = interpolate_layout(
                    interpolate_layout_from, loc, finder, mapped=True)
                font['GPOS'] = gpos_src['GPOS']
                gsub_src = TTFont(
                    finder(self._closest_location(master_locations, loc)))
                if 'GDEF' in gsub_src:
                    font['GDEF'] = gsub_src['GDEF']
                if 'GSUB' in gsub_src:
                    font['GSUB'] = gsub_src['GSUB']

            if do_autohint:
                # if we are autohinting, we save the unhinted font to a
                # temporary path, and the hinted one to the final destination
                fd, otf_path = tempfile.mkstemp("."+ext)
                os.close(fd)
            elif output_path is None:
                otf_path = self._output_path(ufo, ext, is_instance,
                                             interpolatable,
                                             output_dir=output_dir)
            else:
                otf_path = output_path

            logger.info("Saving %s", otf_path)
            font.save(otf_path)

            # 'subset' is an Optional[bool], can be None, True or False.
            # When False, we never subset; when True, we always do; when
            # None (default), we check the presence of custom parameters
            if subset is False:
                pass
            elif subset is True or (
                (
                    KEEP_GLYPHS_OLD_KEY in ufo.lib
                    or KEEP_GLYPHS_NEW_KEY in ufo.lib
                )
                or any(
                    glyph.lib.get(GLYPH_EXPORT_KEY, True) is False
                    for glyph in ufo
                )
            ):
                self.subset_otf_from_ufo(otf_path, ufo)

            if not do_autohint:
                continue

            if output_path is not None:
                hinted_otf_path = output_path
            else:
                hinted_otf_path = self._output_path(
                    ufo, ext, is_instance, interpolatable, autohinted=True,
                    output_dir=output_dir)
            try:
                ttfautohint(otf_path, hinted_otf_path, args=autohint)
            except TTFAError:
                # copy unhinted font to destination before re-raising error
                shutil.copyfile(otf_path, hinted_otf_path)
                raise
            finally:
                # must clean up temp file
                os.remove(otf_path)

    def subset_otf_from_ufo(self, otf_path, ufo):
        """Subset a font using export flags set by glyphsLib.

        There are two more settings that can change export behavior:
        "Export Glyphs" and "Remove Glyphs", which are currently not supported
        for complexity reasons. See
        https://github.com/googlei18n/glyphsLib/issues/295.
        """
        from fontTools import subset

        # ufo2ft always inserts a ".notdef" glyph as the first glyph
        ufo_order = makeOfficialGlyphOrder(ufo)
        if ".notdef" not in ufo_order:
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

        include = []
        for source_name, binary_name in zip(ufo_order, ot_order):
            if keep_glyphs and source_name not in keep_glyphs:
                continue

            if source_name in ufo:
                exported = ufo[source_name].lib.get(GLYPH_EXPORT_KEY, True)
                if not exported:
                    continue

            include.append(binary_name)

        # copied from nototools.subset
        opt = subset.Options()
        opt.name_IDs = ['*']
        opt.name_legacy = True
        opt.name_languages = ['*']
        opt.layout_features = ['*']
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
            self, glyphs_path, designspace_path=None, master_dir=None,
            instance_dir=None, family_name=None, mti_source=None, **kwargs):
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
            kwargs: Arguments passed along to run_from_designspace.
        """

        logger.info('Building master UFOs and designspace from Glyphs source')
        designspace_path = self.build_master_ufos(
            glyphs_path,
            designspace_path=designspace_path,
            master_dir=master_dir,
            instance_dir=instance_dir,
            family_name=family_name,
            mti_source=mti_source)
        self.run_from_designspace(designspace_path, **kwargs)

    def run_from_designspace(
            self, designspace_path, interpolate=False,
            masters_as_instances=False,
            interpolate_binary_layout=False, round_instances=False,
            **kwargs):
        """Run toolchain from a MutatorMath design space document.

        Args:
            designspace_path: Path to designspace document.
            interpolate: If True output all instance fonts, otherwise just
                masters. If the value is a string, only build instance(s) that
                match given name. The string is compiled into a regular
                expression and matched against the "name" attribute of
                designspace instances using `re.fullmatch`.
            masters_as_instances: If True, output master fonts as instances.
            interpolate_binary_layout: Interpolate layout tables from compiled
                master binaries.
            round_instances: apply integer rounding when interpolating with
                MutatorMath.
            kwargs: Arguments passed along to run_from_ufos.

        Raises:
            TypeError: "variable" output is incompatible with arguments
                "interpolate", "masters_as_instances", and
                "interpolate_binary_layout".
        """

        if "variable" in kwargs.get("output", ()):
            for argname in ("interpolate", "masters_as_instances",
                            "interpolate_binary_layout"):
                if locals()[argname]:
                    raise TypeError(
                        '"%s" argument incompatible with "variable" output'
                        % argname)

        from glyphsLib.interpolation import apply_instance_data
        from mutatorMath.ufo.document import DesignSpaceDocumentReader

        ufos = []
        reader = DesignSpaceDocumentReader(designspace_path, ufoVersion=3,
                                           roundGeometry=round_instances,
                                           verbose=True)
        if not interpolate or masters_as_instances:
            ufos.extend(reader.getSourcePaths())
        if interpolate:
            logger.info('Interpolating master UFOs from designspace')
            if isinstance(interpolate, basestring):
                instances = self._search_instances(designspace_path,
                                                   pattern=interpolate)
                for instance_name in instances:
                    reader.readInstance(("name", instance_name))
                filenames = set(instances.values())
            else:
                reader.readInstances()
                filenames = None  # will include all instances
            logger.info('Applying instance data from designspace')
            ufos.extend(apply_instance_data(designspace_path,
                                            include_filenames=filenames))

        if interpolate_binary_layout is False:
            interpolate_layout_from = interpolate_layout_dir = None
        else:
            interpolate_layout_from = designspace_path
            if isinstance(interpolate_binary_layout, basestring):
                interpolate_layout_dir = interpolate_binary_layout
            else:
                interpolate_layout_dir = None

        self.run_from_ufos(
            ufos, designspace_path=designspace_path,
            is_instance=(interpolate or masters_as_instances),
            interpolate_layout_from=interpolate_layout_from,
            interpolate_layout_dir=interpolate_layout_dir,
            **kwargs)

    def run_from_ufos(
            self, ufos, output=(), designspace_path=None, **kwargs):
        """Run toolchain from UFO sources.

        Args:
            ufos: List of UFO sources, as either paths or opened objects.
            output: List of output formats to generate.
            designspace_path: Path to a MutatorMath designspace, used to
                generate variable font if requested.
            kwargs: Arguments passed along to save_otfs.

        Raises:
            TypeError: 'variable' specified in output formats but designspace
                path not provided.
        """

        if set(output) == set(['ufo']):
            return
        if hasattr(ufos[0], 'path'):
            ufo_paths = [ufo.path for ufo in ufos]
        else:
            if isinstance(ufos, str):
                ufo_paths = glob.glob(ufos)
            else:
                ufo_paths = ufos
            ufos = [Font(path) for path in ufo_paths]

        need_reload = False
        if 'otf' in output:
            self.build_otfs(ufos, **kwargs)
            need_reload = True

        if 'ttf' in output:
            if need_reload:
                ufos = [Font(path) for path in ufo_paths]
            self.build_ttfs(ufos, **kwargs)
            need_reload = True

        tempdirs = []
        if 'ttf-interpolatable' in output or 'variable' in output:
            if need_reload:
                ufos = [Font(path) for path in ufo_paths]
            if 'variable' in output and 'ttf-interpolatable' not in output:
                # when output is only 'variable', we create the master ttfs in
                # a temporary folder; 'output_dir' is the directory where the
                # variable font is saved
                output_dir = kwargs.pop("output_dir", None)
                master_bin_dir = tempfile.mkdtemp(prefix="ttf-interp-")
                tempdirs.append(master_bin_dir)
            else:
                output_dir = master_bin_dir = kwargs.pop("output_dir", None)
            output_path = kwargs.pop("output_path", None)
            self.build_interpolatable_ttfs(
                ufos, output_dir=master_bin_dir, **kwargs)

        if 'variable' in output:
            if designspace_path is None:
                raise TypeError('Need designspace to build variable font.')
            try:
                self.build_variable_font(designspace_path,
                                         output_path=output_path,
                                         output_dir=output_dir,
                                         master_bin_dir=master_bin_dir)
            finally:
                for tempdir in tempdirs:
                    shutil.rmtree(tempdir)

    @staticmethod
    def _search_instances(designspace_path, pattern):
        designspace = designspaceLib.DesignSpaceDocument()
        designspace.read(designspace_path)
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
        return '%s-%s' % (ufo.info.familyName.replace(' ', ''),
                          ufo.info.styleName.replace(' ', ''))

    def _output_dir(self, ext, is_instance=False, interpolatable=False,
                    autohinted=False, is_variable=False):
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
            dir_prefix = 'variable_'
        elif is_instance:
            dir_prefix = 'instance_'
        else:
            dir_prefix = 'master_'
        dir_suffix = '_interpolatable' if interpolatable else ''
        output_dir = dir_prefix + ext + dir_suffix
        if autohinted:
            output_dir = os.path.join('autohinted', output_dir)
        return output_dir

    def _output_path(self, ufo_or_font_name, ext, is_instance=False,
                     interpolatable=False, autohinted=False,
                     is_variable=False, output_dir=None):
        """Generate output path for a font file with given extension."""

        if isinstance(ufo_or_font_name, basestring):
            font_name = ufo_or_font_name
        elif ufo_or_font_name.path:
            font_name = os.path.splitext(os.path.basename(
                os.path.normpath(ufo_or_font_name.path)))[0]
        else:
            font_name = self._font_name(ufo_or_font_name)

        if output_dir is None:
            output_dir = self._output_dir(
                ext, is_instance, interpolatable, autohinted, is_variable)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        return os.path.join(output_dir, '%s.%s' % (font_name, ext))

    def _designspace_locations(self, designspace_path):
        """Map font filenames to their locations in a designspace."""

        maps = []
        ds = designspaceLib.DesignSpaceDocument()
        ds.read(designspace_path)
        for elements in (ds.sources, ds.instances):
            location_map = {}
            for element in elements:
                path = _normpath(os.path.join(
                    os.path.dirname(designspace_path), element.filename))
                location_map[path] = element.location
            maps.append(location_map)
        return maps

    def _closest_location(self, location_map, target):
        """Return path of font whose location is closest to target."""

        dist = lambda a, b: math.sqrt(sum((a[k] - b[k]) ** 2 for k in a.keys()))
        paths = iter(location_map.keys())
        closest = next(paths)
        closest_dist = dist(target, location_map[closest])
        for path in paths:
            cur_dist = dist(target, location_map[path])
            if cur_dist < closest_dist:
                closest = path
                closest_dist = cur_dist
        return closest


class FDKFeatureCompiler(FeatureCompiler):
    """An OTF compiler which uses the AFDKO to compile feature syntax."""

    def buildTables(self):
        if not self.features.strip():
            return

        import subprocess
        from fontTools.misc.py23 import tostr

        outline_path = feasrc_path = fea_path = None
        try:
            fd, outline_path = tempfile.mkstemp()
            os.close(fd)
            self.ttFont.save(outline_path)

            fd, feasrc_path = tempfile.mkstemp()
            os.close(fd)

            fd, fea_path = tempfile.mkstemp()
            os.write(fd, tobytes(self.features, encoding='utf-8'))
            os.close(fd)

            process = subprocess.Popen(
                [
                    "makeotf",
                    "-o",
                    feasrc_path,
                    "-f",
                    outline_path,
                    "-ff",
                    fea_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = process.communicate()
            retcode = process.poll()

            report = tostr(stdout + (b"\n" + stderr if stderr else b""))
            logger.info(report)

            # before afdko >= 2.7.1rc1, makeotf did not exit with non-zero
            # on failure, so we have to parse the error message
            if retcode != 0:
                success = False
            else:
                success = (
                    "makeotf [Error] Failed to build output font" not in report
                )
                if success:
                    with TTFont(feasrc_path) as feasrc:
                        for table in ["GDEF", "GPOS", "GSUB"]:
                            if table in feasrc:
                                self.ttFont[table] = feasrc[table]
            if not success:
                raise FontmakeError("Feature syntax compilation failed.")
        finally:
            for path in (outline_path, fea_path, feasrc_path):
                if path is not None:
                    os.remove(path)


def _varLib_finder(source, directory="", ext="ttf"):
    """Finder function to be used with varLib.build to find master TTFs given
    the filename of the source UFO master as specified in the designspace.
    It replaces the UFO directory with the one specified in 'directory'
    argument, and replaces the file extension with 'ext'.
    """
    fname = os.path.splitext(os.path.basename(source))[0] + '.' + ext
    return os.path.join(directory, fname)


def _normpath(fname):
    return os.path.normcase(os.path.normpath(fname))
