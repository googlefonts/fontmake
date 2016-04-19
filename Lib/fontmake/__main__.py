# Copyright 2015 Google Inc. All Rights Reserved.
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


from argparse import ArgumentParser
from fontmake.font_project import FontProject


def main():
    parser = ArgumentParser()
    parser.add_argument('-g', '--glyphs-path')
    parser.add_argument('-u', '--ufo-paths', nargs='+')
    parser.add_argument('-m', '--mm-designspace')
    parser.add_argument('-o', '--output', nargs='+', default=('otf', 'ttf'),
                        choices=('otf', 'ttf', 'ttf-interpolatable'))
    parser.add_argument('-i', '--interpolate', action='store_true',
                        help='interpolate masters (Glyphs source only)')
    parser.add_argument('--mti-source')
    parser.add_argument('--use-afdko', action='store_true')
    args = vars(parser.parse_args())

    project = FontProject()

    glyphs_path = args.pop('glyphs_path')
    ufo_paths = args.pop('ufo_paths')
    designspace_path = args.pop('mm_designspace')
    if not sum(1 for p in [glyphs_path, ufo_paths, designspace_path] if p) == 1:
        raise ValueError('Exactly one source type required (Glyphs or UFO).')

    if glyphs_path:
        project.run_from_glyphs(glyphs_path, **args)

    elif designspace_path:
        project.run_from_designspace(designspace_path, **args)

    else:
        excluded = 'interpolate'
        if args[excluded]:
            raise ValueError(
                '"%s" argument only available for Glyphs or Designspace source'
                % excluded)
        del args[excluded]

    if ufo_paths:
        project.run_from_ufos(ufo_paths, **args)


if __name__ == '__main__':
    main()
