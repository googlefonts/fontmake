# Copyright 2016 Google Inc. All Rights Reserved.
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
import unittest

from fontTools.ttLib import TTFont


HERE = os.path.dirname(__file__)


class TestAvarOutput(unittest.TestCase):
    def _get_font(self):
        return TTFont(os.path.join(
            HERE, 'AvarDesignspaceTest', 'instance_ttf', 'MyFont-Regular.ttf'))

    def test_weight_classes(self):
        font = self._get_font()
        self.assertEqual(font['OS/2'].usWeightClass, 400)

    def test_interpolation(self):
        font = self._get_font()
        glyph_set = font.getGlyphSet()
        glyph = glyph_set['uni006C']._glyph
        self.assertEqual(glyph.xMin, 50)
        self.assertEqual(glyph.xMax, 170)


class TestSubsetOutput(unittest.TestCase):

    def test_glyph_order(self):
        for ext in ("otf", "ttf"):
            font = TTFont(
                os.path.join(
                    HERE,
                    "instance_%s" % ext,
                    "Test-SubsetRegular.%s" % ext
                )
            )
            self.assertEqual(
                font.getGlyphOrder(),
                [".notdef", "space", "A", "C", "B"],
            )


if __name__ == '__main__':
    unittest.main()
