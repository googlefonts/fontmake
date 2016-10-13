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
    parser.add_argument(
        '-o', '--output', nargs='+', default=('otf', 'ttf'),
        choices=('ufo', 'otf', 'ttf', 'ttf-interpolatable', 'variable'))

    parser.add_argument(
        '-i', '--interpolate', action='store_true',
        help='Interpolate masters (for Glyphs or MutatorMath sources only)')
    parser.add_argument(
        '-M', '--masters-as-instances', action='store_true',
        help='Output masters as instances')
    parser.add_argument(
        '--family-name',
        help='Family name to use for masters, and to filter output instances')

    parser.add_argument(
        '--mti-source')
    parser.add_argument(
        '--interpolate-binary-layout', action='store_true',
        help='Interpolate layout tables from compiled master binaries. '
             'Requires Glyphs or MutatorMath source.')
    parser.add_argument(
        '--use-afdko', action='store_true')

    parser.add_argument(
        '-a', '--autohint', nargs='?', const='',
        help='Run ttfautohint. Can provide arguments, quoted')
    parser.add_argument(
        '--keep-direction', dest='reverse_direction', action='store_false',
        help='Do not reverse contour direction when output is ttf or '
             'ttf-interpolatable')
    parser.add_argument(
        '--keep-overlaps', dest='remove_overlaps', action='store_false',
        help='Do not remove any overlap.')

    group1 = parser.add_mutually_exclusive_group(required=False)
    group1.add_argument(
        '--production-names', dest='use_production_names', action='store_true',
        help='Rename glyphs with production names if available otherwise use '
             'uninames.')
    group1.add_argument(
        '--no-production-names', dest='use_production_names',
        action='store_false')

    group2 = parser.add_mutually_exclusive_group(required=False)
    group2.add_argument(
        '--subset', dest='subset', action='store_true',
        help='Subset font using export flags set by glyphsLib')
    group2.add_argument(
        '--no-subset', dest='subset', action='store_false')

    group3 = parser.add_mutually_exclusive_group(required=False)
    group3.add_argument(
        '-s', '--subroutinize', action='store_true',
        help='Optimize CFF table using compreffor (default)')
    group3.add_argument(
        '-S', '--no-subroutinize', dest='subroutinize', action='store_false')
    parser.add_argument(
        '-e', '--conversion-error', type=float, default=None, metavar='ERROR',
        help='Maximum approximation error for cubic to quadratic conversion '
             'measured in EM')

    parser.set_defaults(use_production_names=None, subset=None,
                        subroutinize=True)

    parser.add_argument('--timing', action='store_true')
    parser.add_argument('--verbose', default='INFO')
    args = vars(parser.parse_args())

    project = FontProject(timing=args.pop('timing'),
                          verbosity=args.pop('verbose'))

    glyphs_path = args.pop('glyphs_path')
    ufo_paths = args.pop('ufo_paths')
    designspace_path = args.pop('mm_designspace')
    if sum(1 for p in [glyphs_path, ufo_paths, designspace_path] if p) != 1:
        parser.error('Exactly one source type required (Glyphs, UFO, or '
                     'MutatorMath).')

    def exclude_args(parser, args, excluded_args, source_name):
        msg = '"%s" argument only available for %s source'
        for excluded in excluded_args:
            if args[excluded]:
                parser.error(msg % (excluded, source_name))
            del args[excluded]

    if glyphs_path:
        project.run_from_glyphs(glyphs_path, **args)
        return

    exclude_args(parser, args, ['family_name'], 'Glyphs')
    if designspace_path:
        project.run_from_designspace(designspace_path, **args)
        return

    exclude_args(
        parser, args, ['interpolate', 'interpolate_binary_layout'],
        'Glyphs or MutatorMath')
    project.run_from_ufos(
        ufo_paths, is_instance=args.pop('masters_as_instances'), **args)


if __name__ == '__main__':
    main()
