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


import os
import plistlib
import re
import tempfile
from time import time

from booleanOperations import BooleanOperationManager
from cu2qu.rf import fonts_to_quadratic
from glyphs2ufo.glyphslib import build_masters, build_instances
from ufo2ft import compileOTF, compileTTF
from ufo2ft.kernFeatureWriter import KernFeatureWriter


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
            contours = glyph.contours
            glyph.clearContours()
            manager.union(contours, glyph.getPointPen())

    def decompose_glyph(self, ufo, glyph):
        """Moves the components of a glyph to its outline."""

        self._deep_copy_contours(ufo, glyph, glyph, (0, 0), (1, 1))
        glyph.clearComponents()

    def _deep_copy_contours(self, ufo, parent, component, offset, scale):
        """Copy contours from component to parent, including nested components."""

        for nested in component.components:
            self._deep_copy_contours(
                ufo, parent, ufo[nested.baseGlyph],
                (offset[0] + nested.offset[0], offset[1] + nested.offset[1]),
                (scale[0] * nested.scale[0], scale[1] * nested.scale[1]))

        if component == parent:
            return
        for contour in component:
            contour = contour.copy()
            contour.scale(scale)
            contour.move(offset)
            parent.appendContour(contour)

    def save_otf(self, ufo, is_instance=False, mti_feafiles=None,
                 kern_writer=KernFeatureWriter):
        """Build OTF from UFO."""

        otf_path = self._output_path(ufo, 'otf', is_instance)
        otf = compileOTF(ufo, kernWriter=kern_writer, mtiFeaFiles=mti_feafiles)
        otf.save(otf_path)

    def save_ttf(self, ufo, is_instance=False, mti_feafiles=None,
                 kern_writer=KernFeatureWriter):
        """Build TTF from UFO."""

        ttf_path = self._output_path(ufo, 'ttf', is_instance)
        ttf = compileTTF(ufo, kernWriter=kern_writer, mtiFeaFiles=mti_feafiles)
        ttf.save(ttf_path)

    def run_all(
        self, glyphs_path, preprocess=True, interpolate=False,
        compatible=False, remove_overlaps=True, mti_source=None):
        """Run toolchain from Glyphs source to OpenType binaries."""

        is_italic = 'Italic' in glyphs_path

        mti_paths = {}
        if mti_source:
            mti_paths = plistlib.readPlist(mti_source)
            src_dir = os.path.dirname(glyphs_path)
            for paths in mti_paths.values():
                for table in ('GDEF', 'GPOS', 'GSUB'):
                    paths[table] = os.path.join(src_dir, paths[table])

        if preprocess:
            print '>> Checking Glyphs source for illegal glyph names'
            glyphs_source = self.preprocess(glyphs_path)
            fd, glyphs_path = tempfile.mkstemp()
            with os.fdopen(fd, 'w') as fp:
                fp.write(glyphs_source)

        if interpolate:
            print '>> Interpolating master UFOs from Glyphs source'
            ufos = self.build_instances(glyphs_path, is_italic)
        else:
            print '>> Loading master UFOs from Glyphs source'
            ufos = self.build_masters(glyphs_path, is_italic)

        if preprocess:
            os.remove(glyphs_path)

        if remove_overlaps and not compatible:
            for ufo in ufos:
                print '>> Removing overlaps for ' + ufo.info.postscriptFullName
                self.remove_overlaps(ufo)

        for ufo in ufos:
            name = ufo.info.postscriptFullName
            print '>> Saving OTF for ' + name
            self.save_otf(
                ufo, is_instance=interpolate, mti_feafiles=mti_paths.get(name),
                kern_writer=GlyphsKernWriter)

        start_t = time()
        if compatible:
            print '>> Converting curves to quadratic'
            fonts_to_quadratic(ufos, dump_stats=True)
        else:
            for ufo in ufos:
                print '>> Converting curves for ' + ufo.info.postscriptFullName
                fonts_to_quadratic([ufo], dump_stats=True)
        t = time() - start_t
        print '[took %f seconds]' % t

        for ufo in ufos:
            name = ufo.info.postscriptFullName
            print '>> Saving TTF for ' + name
            self.save_ttf(
                ufo, is_instance=interpolate, mti_feafiles=mti_paths.get(name),
                kern_writer=GlyphsKernWriter)

    def _output_dir(self, ext, is_instance=False):
        """Generate an output directory."""

        dir_prefix = 'instance_' if is_instance else 'master_'
        return os.path.join(dir_prefix + ext)

    def _output_path(self, ufo, ext, is_instance=False):
        """Generate output path for a UFO with given directory and extension."""

        family = ufo.info.familyName.replace(' ', '')
        style = ufo.info.styleName.replace(' ', '')
        out_dir = self._output_dir(ext, is_instance)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        return os.path.join(out_dir, '%s-%s.%s' % (family, style, ext))


class GlyphsKernWriter(KernFeatureWriter):
    """A ufo2ft kerning feature writer which looks for UFO kerning groups with
    names matching the old MMK pattern (which is used by Glyphs)."""

    leftUfoGroupRe = r"@MMK_L_(.+)"
    rightUfoGroupRe = r"@MMK_R_(.+)"
