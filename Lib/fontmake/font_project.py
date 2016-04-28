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

import glob
import logging
import os
import plistlib
import re
import tempfile
import time

from booleanOperations import BooleanOperationManager
from cu2qu.ufo import font_to_quadratic, fonts_to_quadratic
from defcon import Font
from fontTools import subset
from fontTools.misc.loggingTools import configLogger, Timer
from fontTools.misc.transform import Identity
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont
from glyphsLib import build_masters, build_instances
from mutatorMath.ufo import build as build_designspace
from mutatorMath.ufo.document import DesignSpaceDocumentReader
from ufo2ft import compileOTF, compileTTF
from ufo2ft.makeotfParts import FeatureOTFCompiler

timer = Timer(logging.getLogger('fontmake'), level=logging.DEBUG)

PUBLIC_PREFIX = 'public.'
GLYPHS_PREFIX = 'com.schriftgestaltung.'


class FontProject:
    """Provides methods for building fonts."""

    @staticmethod
    def preprocess(glyphs_path):
        """Return Glyphs source with illegal glyph/class names changed."""

        with open(glyphs_path) as fp:
            text = fp.read()
        names = set(re.findall('\n(?:glyph)?name = "(.+-.+)";\n', text))

        if names:
            num_names = len(names)
            printed_names = sorted(names)[:5]
            if num_names > 5:
                printed_names.append('...')
            print('Found %s glyph names containing hyphens: %s' % (
                num_names, ', '.join(printed_names)))
            print('Replacing all hyphens with periods.')

        for old_name in names:
            new_name = old_name.replace('-', '.')
            text = text.replace(old_name, new_name)
        return text

    def __init__(self, timing=False):
        if timing:
            configLogger(logger=timer.logger, level=logging.DEBUG)

    @timer()
    def build_ufos(self, glyphs_path, is_italic=False, interpolate=False):
        """Build UFOs from Glyphs source."""

        master_dir = self._output_dir('ufo')
        instance_dir = self._output_dir('ufo', is_instance=True)
        if interpolate:
            return build_instances(glyphs_path, master_dir, instance_dir,
                                   is_italic)
        else:
            return build_masters(glyphs_path, master_dir, is_italic,
                                 designspace_instance_dir=instance_dir)

    @timer()
    def remove_overlaps(self, ufos):
        """Remove overlaps in UFOs' glyphs' contours."""

        manager = BooleanOperationManager()
        for ufo in ufos:
            print('>> Removing overlaps for ' + self._font_name(ufo))
            for glyph in ufo:
                contours = list(glyph)
                glyph.clearContours()
                manager.union(contours, glyph.getPointPen())

    @timer()
    def decompose_glyphs(self, ufos):
        """Move components of UFOs' glyphs to their outlines."""

        for ufo in ufos:
            print('>> Decomposing glyphs for ' + self._font_name(ufo))
            for glyph in ufo:
                self._deep_copy_contours(ufo, glyph, glyph, Identity)
                glyph.clearComponents()

    def _deep_copy_contours(self, ufo, parent, component, transformation):
        """Copy contours from component to parent, including nested components."""

        for nested in component.components:
            self._deep_copy_contours(
                ufo, parent, ufo[nested.baseGlyph],
                transformation.transform(nested.transformation))

        if component != parent:
            component.draw(TransformPen(parent.getPen(), transformation))

    @timer()
    def convert_curves(self, ufos, compatible=False):
        if compatible:
            fonts_to_quadratic(ufos, dump_stats=True)
        else:
            for ufo in ufos:
                print('>> Converting curves for ' + self._font_name(ufo))
                font_to_quadratic(ufo, dump_stats=True)

    def build_otfs(self, ufos, **kwargs):
        """Build OpenType binaries with CFF outlines."""

        print('\n>> Building OTFs')

        self.decompose_glyphs(ufos)
        self.remove_overlaps(ufos)
        self.save_otfs(ufos, **kwargs)

    def build_ttfs(self, ufos, **kwargs):
        """Build OpenType binaries with TrueType outlines."""

        print('\n>> Building TTFs')

        self.remove_overlaps(ufos)
        self.convert_curves(ufos)
        self.save_otfs(ufos, ttf=True, **kwargs)

    def build_interpolatable_ttfs(self, ufos, **kwargs):
        """Build OpenType binaries with interpolatable TrueType outlines."""

        print('\n>> Building interpolation-compatible TTFs')

        self.convert_curves(ufos, compatible=True)
        self.save_otfs(ufos, ttf=True, interpolatable=True, **kwargs)

    @timer()
    def save_otfs(
            self, ufos, ttf=False, interpolatable=False, mti_paths=None,
            is_instance=False, use_afdko=False, subset=True):
        """Write OpenType binaries."""

        ext = 'ttf' if ttf else 'otf'
        fea_compiler = FDKFeatureCompiler if use_afdko else FeatureOTFCompiler
        otf_compiler = compileTTF if ttf else compileOTF

        for ufo in ufos:
            name = self._font_name(ufo)
            print('>> Saving %s for %s' % (ext.upper(), name))

            otf_path = self._output_path(ufo, ext, is_instance, interpolatable)
            otf = otf_compiler(
                ufo, featureCompilerClass=fea_compiler,
                mtiFeaFiles=mti_paths[name] if mti_paths is not None else None)
            otf.save(otf_path)

            if subset:
                self.subset_otf_from_ufo(otf_path, ufo)
            self.rename_glyphs_from_ufo(otf_path, ufo)

    def subset_otf_from_ufo(self, otf_path, ufo):
        """Subset a font using export flags set by glyphsLib."""

        font_lib_prefix = GLYPHS_PREFIX
        glyph_lib_prefix = font_lib_prefix + 'Glyphs.'

        keep_glyphs = set(ufo.lib.get(font_lib_prefix + 'Keep Glyphs', []))

        include = []
        glyph_order = ufo.lib['public.glyphOrder']
        for glyph_name in glyph_order:
            glyph = ufo[glyph_name]
            if ((keep_glyphs and glyph_name not in keep_glyphs) or
                not glyph.lib.get(glyph_lib_prefix + 'Export', True)):
                continue
            include.append(glyph_name)

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

    def rename_glyphs_from_ufo(self, otf_path, ufo):
        """Rename glyphs using glif.lib.public.postscriptNames in UFO."""

        if ufo.lib.get(GLYPHS_PREFIX + "Don't use Production Names"):
            return

        rename_map = {}
        for glyph in ufo:
            production_name = glyph.lib.get(PUBLIC_PREFIX + 'postscriptName')
            if production_name:
                rename_map[glyph.name] = production_name
        rename = lambda names: [rename_map.get(n, n) for n in names]

        font = TTFont(otf_path)
        font.setGlyphOrder(rename(font.getGlyphOrder()))
        if 'CFF ' in font:
            cff = font['CFF '].cff.topDictIndex[0]
            char_strings = cff.CharStrings.charStrings
            cff.CharStrings.charStrings = {
                rename_map.get(n, n): v for n, v in char_strings.items()}
            cff.charset = rename(cff.charset)
        font.save(otf_path)

    def run_from_glyphs(
            self, glyphs_path, preprocess=True, interpolate=False, **kwargs):
        """Run toolchain from Glyphs source to OpenType binaries."""

        is_italic = 'Italic' in glyphs_path

        if preprocess:
            print('>> Checking Glyphs source for illegal glyph names')
            glyphs_source = self.preprocess(glyphs_path)
            tmp_glyphs_file = tempfile.NamedTemporaryFile()
            glyphs_path = tmp_glyphs_file.name
            tmp_glyphs_file.write(glyphs_source)
            tmp_glyphs_file.seek(0)

        print('>> Building UFOs from Glyphs source')
        ufos = self.build_ufos(glyphs_path, is_italic, interpolate)
        self.run_from_ufos(ufos, is_instance=interpolate, **kwargs)

    def run_from_designspace(
            self, designspace_path, interpolate=False, **kwargs):
        """Run toolchain from a MutatorMath design space document to OpenType
        binaries.
        """

        if interpolate:
            print('>> Interpolating master UFOs from design space')
            results = build_designspace(
                designspace_path, outputUFOFormatVersion=3)
            ufos = []
            for result in results:
                ufos.extend(result.values())
        else:
            reader = DesignSpaceDocumentReader(designspace_path, ufoVersion=3)
            ufos = reader.getSourcePaths()
        self.run_from_ufos(ufos, is_instance=True, **kwargs)

    def run_from_ufos(self, ufos, output=(), mti_source=None, **kwargs):
        """Run toolchain from UFO sources to OpenType binaries."""

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

        mti_paths = None
        if mti_source:
            mti_paths = {}
            mti_paths = plistlib.readPlist(mti_source)
            src_dir = os.path.dirname(mti_source)
            for paths in mti_paths.values():
                for table in ('GDEF', 'GPOS', 'GSUB'):
                    paths[table] = os.path.join(src_dir, paths[table])

        need_reload = False
        if 'otf' in output:
            self.build_otfs(ufos, mti_paths=mti_paths, **kwargs)
            need_reload = True

        if 'ttf' in output:
            if need_reload:
                ufos = [Font(path) for path in ufo_paths]
            self.build_ttfs(ufos, mti_paths=mti_paths, **kwargs)
            need_reload = True

        if 'ttf-interpolatable' in output:
            if need_reload:
                ufos = [Font(path) for path in ufo_paths]
            self.build_interpolatable_ttfs(ufos, mti_paths=mti_paths, **kwargs)

    def _font_name(self, ufo):
        return '%s-%s' % (ufo.info.familyName.replace(' ', ''),
                          ufo.info.styleName.replace(' ', ''))

    def _output_dir(self, ext, is_instance=False, interpolatable=False):
        """Generate an output directory."""

        dir_prefix = 'instance_' if is_instance else 'master_'
        dir_suffix = '_interpolatable' if interpolatable else ''
        return dir_prefix + ext + dir_suffix

    def _output_path(self, ufo, ext, is_instance=False, interpolatable=False):
        """Generate output path for a font file with given extension."""

        out_dir = self._output_dir(ext, is_instance, interpolatable)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        return os.path.join(out_dir, '%s.%s' % (self._font_name(ufo), ext))


class FDKFeatureCompiler(FeatureOTFCompiler):
    """An OTF compiler which uses the AFDKO to compile feature syntax."""

    def setupFile_featureTables(self):
        if self.mtiFeaFiles is not None:
            super(FDKFeatureCompiler, self).setupFile_featureTables()

        elif not self.features.strip():
            return

        import subprocess
        from fontTools.misc.py23 import tostr

        fd, outline_path = tempfile.mkstemp()
        os.close(fd)
        self.outline.save(outline_path)

        fd, feasrc_path = tempfile.mkstemp()
        os.close(fd)

        fd, fea_path = tempfile.mkstemp()
        os.write(fd, self.features)
        os.close(fd)

        report = tostr(subprocess.check_output([
            "makeotf", "-o", feasrc_path, "-f", outline_path,
            "-ff", fea_path]))
        os.remove(outline_path)
        os.remove(fea_path)

        print(report)
        success = "Done." in report
        if success:
            feasrc = TTFont(feasrc_path)
            for table in ["GDEF", "GPOS", "GSUB"]:
                if table in feasrc:
                    self.outline[table] = feasrc[table]

        feasrc.close()
        os.remove(feasrc_path)
        if not success:
            raise ValueError("Feature syntax compilation failed.")
