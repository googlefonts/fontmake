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
from os import path
import re
from time import time

from booleanOperations import BooleanOperationManager
from cu2qu import fonts_to_quadratic
from glyphs2ufo.glyphslib import build_masters, build_instances
from robofab.world import OpenFont
from ufo2ft import compileOTF, compileTTF


class FontProject:
    """Provides methods for building fonts."""

    def __init__(self, src_dir, out_dir):
        self.src_dir = src_dir
        self.out_dir = out_dir

    def preprocess(self, glyphs_path):
        """Return Glyphs source with illegal glyph names changed."""

        with open(glyphs_path) as fp:
            text = fp.read()
        names = re.findall('\nglyphname = "(.+-.+)";\n', text)
        for old_name in names:
            new_name = old_name.replace('-', '_')
            print('Found illegal glyph name "%s", replacing all instances in '
                  'source with "%s".' % (old_name, new_name))
            text = text.replace(old_name, new_name)
        return text

    def build_masters(self, glyphs_path, italic=False):
        """Build master UFOs from Glyphs source."""

        return build_masters(glyphs_path, self.src_dir, italic)

    def build_instances(self, glyphs_path, italic=False):
        """Build instance UFOs from Glyphs source."""

        out_dir = self._output_dir('ufo')
        return build_instances(glyphs_path, self.src_dir, out_dir, italic)

    def remove_overlaps(self, ufo):
        """Remove overlaps in a UFO's glyphs' contours."""

        for glyph in ufo:
            manager = BooleanOperationManager()
            contours = glyph.contours
            glyph.clearContours()
            manager.union(contours, glyph.getPointPen())

    def save_otf(self, ufo):
        """Build OTF from UFO."""

        otf_path = self._output_path(ufo, 'otf')
        otf = compileOTF(ufo)
        otf.save(otf_path)

    def save_ttf(self, ufo):
        """Build TTF from UFO."""

        ttf_path = self._output_path(ufo, 'ttf')
        ttf = compileTTF(ufo)
        ttf.save(ttf_path)

    def run_all(
        self, glyphs_path, fea_path=None, compatible=False, interpolate=False,
        remove_overlaps=True, preprocess=True):
        """Run toolchain from Glyphs source to OpenType binaries."""

        italic = 'Italic' in glyphs_path

        if preprocess:
            print '>> Checking Glyphs source for illegal glyph names'
            glyphs_source = self.preprocess(glyphs_path)
            glyphs_path = 'tmp.glyphs'
            with open(glyphs_path, 'w') as fp:
                fp.write(glyphs_source)

        if interpolate:
            print '>> Interpolating master UFOs from Glyphs source'
            ufos = self.build_instances(glyphs_path, italic)
        else:
            print '>> Loading master UFOs from Glyphs source'
            ufos = self.build_masters(glyphs_path, italic)

        if preprocess:
            os.remove(glyphs_path)

        if remove_overlaps and not compatible:
            for ufo in ufos:
                print '>> Removing overlaps for ' + ufo.info.postscriptFullName
                self.remove_overlaps(ufo)

        for ufo in ufos:
            print '>> Saving OTF for ' + ufo.info.postscriptFullName
            self.save_otf(ufo)

        start_t = time()
        if compatible:
            print '>> Converting curves to quadratic'
            print fonts_to_quadratic(*ufos)
        else:
            for ufo in ufos:
                print '>> Converting curves for ' + ufo.info.postscriptFullName
                print fonts_to_quadratic(ufo) + '\n'
        t = time() - start_t
        print '[took %f seconds]' % t

        for ufo in ufos:
            print '>> Saving TTF for ' + ufo.info.postscriptFullName
            self.save_ttf(ufo)

    def _output_dir(self, ext):
        """Generate an output directory."""

        return path.join(self.out_dir, ext.lower())

    def _output_path(self, ufo, ext):
        """Generate output path for a UFO with given directory and extension."""

        family = ufo.info.familyName.replace(' ', '')
        style = ufo.info.styleName.replace(' ', '')
        out_dir = self._output_dir(ext)
        if not path.exists(out_dir):
            os.makedirs(out_dir)
        return path.join(out_dir, '%s-%s.%s' % (family, style, ext))
