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
import sys

from convert_curves import fonts_to_quadratic
from glyphs2ufo.glyphslib import build_masters
from glyphs2ufo.torf import set_redundant_data, clear_data
from mutatorMath.ufo import build as build_instances
from robofab.world import OpenFont
#from ufo2fdk.outlineOTF import OutlineOTFCompiler
from ufo2fdk import OTFCompiler
from ufo2fdk.ttf_compiler import TTFCompiler

from kern_feature import generate_kern_feature
from mark_feature import generate_mark_features


class FontProject:
    """Provides methods for building fonts."""

    def load_masters(self, glyphs_path, debug=False):
        """Build master UFOs and a MutatorMath designspace document writer from
        Glyphs source. Returns the master UFO paths, document writer, and
        instance data as a list of <path, data> pairs.

        If debug is true, returns the unused contents of the Glyphs source.
        """

        src_dir = 'src'
        out_dir = self._output_dir('out', 'ufo')
        return build_masters(
            glyphs_path, src_dir, out_dir, 'Italic' in glyphs_path, debug)

    def interpolate_masters(self, designspace_path, instance_data, debug=False):
        """Build and return instance UFOs using MutatorMath."""

        build_instances(designspace_path)

        ufos = []
        for instance_path, data in instance_data:
            ufo = OpenFont(instance_path)
            panose_values = data.pop('panose', None)
            if panose_values:
                ufo.info.openTypeOS2Panose = map(int, panose_values)
            set_redundant_data(ufo)
            ufos.append(ufo)

        if debug:
            return clear_data(instance_data)
        return ufos

    def build_features(self, font):
        """Build mark/mkmk/kern features from UFO kerning and glyph anchors."""

        generate_mark_features(font)
        generate_kern_feature(font)

    def save_otf(self, ufo):
        """Build OTF from UFO."""

        otf_path = self._output_path(ufo, 'out', 'otf')
        #compiler = OutlineOTFCompiler(ufo, otf_path)
        #compiler.compile()
        compiler = OTFCompiler()
        reports = compiler.compile(ufo, otf_path)
        return reports['makeotf']

    def save_ttf(self, ufo):
        """Build TTF from UFO."""

        ttf_path = self._output_path(ufo, 'out', 'ttf')
        compiler = TTFCompiler(ufo, ttf_path)
        compiler.compile()

    def run_all(self, glyphs_path, interpolate=False):
        """Run toolchain from Glyphs source to OpenType binaries."""

        print '>> Loading master UFOs from Glyphs source'
        ufos, designspace_path, instance_data = self.load_masters(glyphs_path)

        if interpolate:
            print '>> Interpolating masters'
            ufos = self.interpolate_masters(designspace_path, instance_data)

        for ufo in ufos:
            name = ufo.info.postscriptFullName
            self.build_features(ufo)
            print '>> Saving UFO for ' + name
            ufo.save(self._output_path(ufo, 'out', 'ufo'))
            print '>> Saving OTF for ' + name
            print self.save_otf(ufo)

        print '>> Converting curves to quadratic'
        print fonts_to_quadratic(ufos, compatible=True)

        for ufo in ufos:
            name = ufo.info.postscriptFullName
            print '>> Saving TTF for ' + name
            self.save_ttf(ufo)

    def _output_dir(self, build_dir, ext):
        """Generate an output directory."""

        return path.join(build_dir, ext.lower())

    def _output_path(self, ufo, build_dir, ext):
        """Generate output path for a UFO with given directory and extension."""

        family = ufo.info.familyName.replace(' ', '')
        style = ufo.info.styleName.replace(' ', '')
        out_dir = self._output_dir(build_dir, ext)
        if not path.exists(out_dir):
            os.makedirs(out_dir)
        return path.join(out_dir, '%s-%s.%s' % (family, style, ext))


def main(glyphs_path, interpolate=False, *args):
    project = FontProject()
    project.run_all(glyphs_path, interpolate)


if __name__ == '__main__':
    main(*sys.argv[1:])
