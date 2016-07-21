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
                        choices=('ufo', 'otf', 'ttf', 'ttf-interpolatable'))
    parser.add_argument('-i', '--interpolate', action='store_true',
                        help='interpolate masters (for Glyphs or MutatorMath '
                             'sources only)')
    parser.add_argument('-mi', '--masters-as-instances', action='store_true',
                        help='treat masters as instances')
    parser.add_argument('-a', '--autohint', nargs='?',
                        help='can provide arguments to ttfautohint, quoted')
    parser.add_argument('--mti-source')
    parser.add_argument('--family-name', help='Family name to use for masters,'
                        ' and to filter output instances by')
    parser.add_argument('--use-afdko', action='store_true')
    parser.add_argument('--keep-direction', dest="reverse_direction",
                        action='store_false', help='Do not reverse contour '
                        'direction when output is ttf or ttf-interpolatable')
    parser.add_argument('--keep-overlaps', dest="remove_overlaps",
                        action='store_false',
                        help='Do not remove any overlap.')
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--production-names', dest='use_production_names',
                       action='store_true', help='Rename glyphs with '
                       'production names if available otherwise use uninames.')
    group.add_argument('--no-production-names', dest='use_production_names',
                       action='store_false',
                       help='Do not rename glyphs with production names. '
                       'Keeps original glyph names')
    parser.set_defaults(use_production_names=None)
    parser.add_argument('--timing', action='store_true')
    args = vars(parser.parse_args())

    project = FontProject(timing=args.pop('timing'))

    glyphs_path = args.pop('glyphs_path')
    ufo_paths = args.pop('ufo_paths')
    designspace_path = args.pop('mm_designspace')
    if not sum(1 for p in [glyphs_path, ufo_paths, designspace_path] if p) == 1:
        parser.error('Exactly one source type required (Glyphs, UFO, or '
                     'MutatorMath).')

    def exclude_args(parser, args, excluded_args):
        exclusive_msg = '"{}" argument only available for {} source'
        exclusive_src = {'interpolate': 'Glyphs or MutatorMath',
                         'family_name': 'Glyphs'}
        for excluded in excluded_args:
            if args[excluded]:
                parser.error(exclusive_msg.format(
                    excluded,
                    exclusive_src[excluded]))
            del args[excluded]

    if glyphs_path:
        project.run_from_glyphs(glyphs_path, **args)

    elif designspace_path:
        exclude_args(parser, args, ['family_name'])
        project.run_from_designspace(designspace_path, **args)

    else:
        exclude_args(parser, args, ['family_name', 'interpolate'])

    if ufo_paths:
        project.run_from_ufos(
            ufo_paths, is_instance=args.pop('masters_as_instances'), **args)


if __name__ == '__main__':
    main()
