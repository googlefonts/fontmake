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


import argparse
import os
from os import path
from time import time

from convert_curves import fonts_to_quadratic
from glyphs2ufo.glyphslib import build_masters, build_instances
from robofab.world import OpenFont
from ufo2ft import compileOTF, compileTTF


class FontProject:
    """Provides methods for building fonts."""

    def __init__(self, src_dir, out_dir):
        self.src_dir = src_dir
        self.out_dir = out_dir

    def build_masters(self, glyphs_path):
        """Build master UFOs from Glyphs source."""

        return build_masters(
            glyphs_path, self.src_dir, 'Italic' in glyphs_path)

    def build_instances(self, glyphs_path):
        """Build instance UFOs from Glyphs source."""

        out_dir = self._output_dir('ufo')
        return build_instances(
            glyphs_path, self.src_dir, out_dir, 'Italic' in glyphs_path)

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

    def run_all(self, glyphs_path, fea_path=None, interpolate=False):
        """Run toolchain from Glyphs source to OpenType binaries."""

        if interpolate:
            print '>> Interpolating master UFOs from Glyphs source'
            ufos = self.build_instances(glyphs_path)
        else:
            print '>> Loading master UFOs from Glyphs source'
            ufos = self.build_masters(glyphs_path)

        for ufo in ufos:
            print '>> Saving OTF for ' + ufo.info.postscriptFullName
            self.save_otf(ufo)

        print '>> Converting curves to quadratic'
        start_t = time()
        print fonts_to_quadratic(ufos, compatible=True)
        t = time() - start_t
        print '[took %f seconds]' % t

        for ufo in ufos:
            name = ufo.info.postscriptFullName
            print '>> Saving TTF for ' + name
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('glyphs_path', metavar='GLYPHS_PATH')
    parser.add_argument('-i', '--interpolate', action='store_true')
    parser.add_argument('-f', '--fea-path')
    args = parser.parse_args()

    project = FontProject('src', 'out')
    project.run_all(args.glyphs_path, args.fea_path, args.interpolate)


if __name__ == '__main__':
    main()
