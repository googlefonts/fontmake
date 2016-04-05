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
import os
import plistlib
import re
import tempfile
import time

from booleanOperations import BooleanOperationManager
from cu2qu.ufo import fonts_to_quadratic
from defcon import Font
from fontTools import subset
from fontTools.misc.transform import Identity
from fontTools.pens.transformPen import TransformPen
from glyphs2ufo.glyphslib import build_masters, build_instances
from mutatorMath.ufo import build as build_designspace
from ufo2ft import compileOTF, compileTTF
from ufo2ft.makeotfParts import FeatureOTFCompiler


class FontProject:
    """Provides methods for building fonts."""

    def preprocess(self, glyphs_path):
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
            print('Replacing all hyphens with underscores.')

        for old_name in names:
            new_name = old_name.replace('-', '_')
            text = text.replace(old_name, new_name)
        return text

    def build_masters(self, glyphs_path, is_italic=False):
        """Build master UFOs from Glyphs source."""

        master_dir = self._output_dir('ufo')
        return build_masters(glyphs_path, master_dir, is_italic)

    def build_instances(self, glyphs_path, is_italic=False):
        """Build instance UFOs from Glyphs source."""

        master_dir = self._output_dir('ufo')
        instance_dir = self._output_dir('ufo', is_instance=True)
        return build_instances(glyphs_path, master_dir, instance_dir, is_italic)

    def remove_overlaps(self, ufo):
        """Remove overlaps in a UFO's glyphs' contours, decomposing first."""

        for glyph in ufo:
            self.decompose_glyph(ufo, glyph)
            manager = BooleanOperationManager()
            contours = list(glyph)
            glyph.clearContours()
            manager.union(contours, glyph.getPointPen())

    def decompose_glyph(self, ufo, glyph):
        """Moves the components of a glyph to its outline."""

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

    def save_otf(self, ufo, ttf=False, is_instance=False, use_afdko=False,
                 mti_feafiles=None, subset=True):
        """Build OpenType binary from UFO."""

        fea_compiler = FDKFeatureCompiler if use_afdko else FeatureOTFCompiler
        otf_path = self._output_path(ufo, 'ttf' if ttf else 'otf', is_instance)
        otf_compiler = compileTTF if ttf else compileOTF
        otf = otf_compiler(ufo, featureCompilerClass=fea_compiler,
                           mtiFeaFiles=mti_feafiles)
        otf.save(otf_path)

        if subset:
            self.subset_otf_from_ufo(otf_path, ufo)

    def subset_otf_from_ufo(self, otf_path, ufo):
        """Subset a font using export flags set by glyphs2ufo."""

        font_lib_prefix = 'com.schriftgestaltung.'
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

        opt.glyph_names = ufo.lib.get(
            font_lib_prefix + "Don't use Production Names")

        font = subset.load_font(otf_path, opt, lazy=False)
        subsetter = subset.Subsetter(options=opt)
        subsetter.populate(glyphs=include)
        subsetter.subset(font)
        subset.save_font(font, otf_path, opt)

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

        if interpolate:
            print('>> Interpolating master UFOs from Glyphs source')
            ufos = self.build_instances(glyphs_path, is_italic)
        else:
            print('>> Loading master UFOs from Glyphs source')
            ufos = self.build_masters(glyphs_path, is_italic)

        self.run_from_ufos(ufos, is_instance=interpolate, **kwargs)

    def run_from_designspace(self, designspace_path, **kwargs):
        """Run toolchain from a MutatorMath design space document to OpenType
        binaries.
        """

        print('>> Interpolating master UFOs from design space')
        results = build_designspace(designspace_path)
        ufos = []
        for result in results:
            ufos.extend(result.values())
        self.run_from_ufos(ufos, **kwargs)

    def run_from_ufos(
            self, ufos, compatible=False, remove_overlaps=True, mti_source=None,
            **kwargs):
        """Run toolchain from UFO sources to OpenType binaries."""

        if isinstance(ufos, str):
            ufos = glob.glob(ufos)
        if isinstance(ufos[0], str):
            ufos = [Font(ufo) for ufo in ufos]

        if remove_overlaps and not compatible:
            for ufo in ufos:
                print('>> Removing overlaps for ' + self._font_name(ufo))
                self.remove_overlaps(ufo)

        mti_paths = {}
        if mti_source:
            mti_paths = plistlib.readPlist(mti_source)
            src_dir = os.path.dirname(mti_source)
            for paths in mti_paths.values():
                for table in ('GDEF', 'GPOS', 'GSUB'):
                    paths[table] = os.path.join(src_dir, paths[table])

        for ufo in ufos:
            name = self._font_name(ufo)
            print('>> Saving OTF for ' + name)
            self.save_otf(ufo, mti_feafiles=mti_paths.get(name), **kwargs)

        start_t = time.time()
        if compatible:
            print('>> Converting curves to quadratic')
            fonts_to_quadratic(ufos, dump_stats=True)
        else:
            for ufo in ufos:
                print('>> Converting curves for ' + self._font_name(ufo))
                fonts_to_quadratic([ufo], dump_stats=True)
        t = time.time() - start_t
        print('[took %f seconds]' % t)

        for ufo in ufos:
            name = self._font_name(ufo)
            print('>> Saving TTF for ' + name)
            self.save_otf(
                ufo, ttf=True, mti_feafiles=mti_paths.get(name), **kwargs)

    def _font_name(self, ufo):
        return '%s-%s' % (ufo.info.familyName.replace(' ', ''),
                          ufo.info.styleName.replace(' ', ''))

    def _output_dir(self, ext, is_instance=False):
        """Generate an output directory."""

        dir_prefix = 'instance_' if is_instance else 'master_'
        return os.path.join(dir_prefix + ext)

    def _output_path(self, ufo, ext, is_instance=False):
        """Generate output path for a UFO with given directory and extension."""

        out_dir = self._output_dir(ext, is_instance)
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
        from fontTools.ttLib import TTFont
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
