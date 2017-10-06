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
try:
    # unittest.mock is only available for python 3+
    from unittest import mock
    from unittest.mock import patch
except ImportError:
    import mock
    from mock import patch
from fontTools.ttLib import TTFont
from fontmake.font_project import FontProject
import fontmake.__main__ as entry
import fontTools


class TestFunctionsAreCalledByArguments(unittest.TestCase):
    @patch('fontmake.font_project.FontProject.run_from_glyphs')
    def test_run_from_glyphs(self, mock):
        self.assertFalse(mock.called)
        entry.main(['-g', 'someGlyphs.glyph'])
        self.assertTrue(mock.called)

    @patch('fontmake.font_project.FontProject.run_from_designspace')
    def test_run_from_designspace(self, mock):
        self.assertFalse(mock.called)
        entry.main(['-m', 'someDesignspace.designspace'])
        self.assertTrue(mock.called)

    @patch('fontmake.font_project.FontProject.run_from_ufos')
    def test_run_from_ufos(self, mock):
        self.assertFalse(mock.called)
        entry.main(['-u', 'someUfo.ufo'])
        self.assertTrue(mock.called)

    # When you nest patch decorators the mocks are passed in to the decorated
    # function in the same order they applied (the normal python order that
    # decorators are applied). This means from the bottom up. So mock_build_ttfs
    # is the first parameter, then mock_build_otfs.
    @patch('fontmake.font_project.FontProject.build_otfs')
    @patch('fontmake.font_project.FontProject.build_ttfs')
    def test_build_otfs(self, mock_build_ttfs, mock_build_otfs):
        project = FontProject()
        self.assertFalse(mock_build_otfs.called)
        self.assertFalse(mock_build_ttfs.called)
        project.run_from_ufos("path to ufo", output=('otf', 'ttf'))
        self.assertTrue(mock_build_ttfs.called)
        self.assertTrue(mock_build_otfs.called)

    @patch('fontmake.font_project.FontProject.build_interpolatable_ttfs')
    @patch('fontmake.font_project.FontProject.build_variable_font')
    def test_run_from_ufos(self, mock_build_variable_font, mock_build_interpolatable_ttfs):
        project = FontProject()
        self.assertFalse(mock_build_interpolatable_ttfs.called)
        self.assertFalse(mock_build_variable_font.called)
        project.run_from_ufos("path to ufo", output=('variable'), designspace_path="design space")
        self.assertTrue(mock_build_interpolatable_ttfs.called)
        self.assertTrue(mock_build_variable_font.called)


class TestOutputFileName(unittest.TestCase):
    @patch('fontTools.varLib.build')
    @patch('fontTools.ttLib.TTFont.save')
    @patch('fontmake.font_project.FontProject._designspace_locations')
    def test_variable_output_filename(self, mock_designspace_locations, mock_TTFont_save, mock_varLib_build):
        project = FontProject()
        mock_designspace_locations.return_value = {'master1': 'location1'}, None
        mock_varLib_build.return_value = TTFont(), None, None
        project.build_variable_font('path/to/designspace.designspace')
        self.assertTrue(mock_TTFont_save.called)
        self.assertTrue(mock_TTFont_save.call_count == 1)
        self.assertEqual(mock_TTFont_save.call_args, mock.call('variable_ttf/designspace-VF.ttf'))


if __name__ == '__main__':
    unittest.main()
