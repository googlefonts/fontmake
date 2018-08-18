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

from __future__ import print_function, absolute_import
from contextlib import contextmanager
from argparse import ArgumentParser, ArgumentTypeError
from fontmake import __version__
from fontmake.font_project import FontProject
from fontmake.errors import FontmakeError
from ufo2ft.featureWriters import loadFeatureWriterFromString


def _loadFeatureWriters(parser, specs):
    feature_writers = []
    for s in specs:
        if s == 'None':
            # magic value that means "don't generate any features!"
            return []
        try:
            feature_writers.append(loadFeatureWriterFromString(s))
        except Exception as e:
            parser.error(
                "Failed to load --feature-writer:\n  %s: %s"
                 % (type(e).__name__, e)
            )
    return feature_writers


def exclude_args(parser, args, excluded_args, target):
    msg = '"%s" option invalid for %s'
    for argname in excluded_args:
        if argname not in args:
            continue
        if args[argname]:
            optname = "--%s" % argname.replace("_", "-")
            parser.error(msg % (optname, target))
        del args[argname]


@contextmanager
def _make_tempdirs(parser, args):
    output = args["output"]
    tempdirs = []
    for dirname in ("master_dir", "instance_dir"):
        if args.get(dirname) == "{tmp}":
            if "ufo" in output:
                parser.error(
                    "Can't use temporary %s directory with 'ufo' output"
                    % dirname.replace("_dir", ""))
            import tempfile
            td = args[dirname] = tempfile.mkdtemp(prefix=dirname+"_")
            tempdirs.append(td)

    yield tempdirs

    if tempdirs:
        import shutil
        for td in tempdirs:
            shutil.rmtree(td)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument('--version', action='version', version=__version__)
    inputGroup = parser.add_argument_group(
        title='Input arguments',
        description='The following arguments are mutually exclusive.')
    xInputGroup = inputGroup.add_mutually_exclusive_group(required=True)
    xInputGroup.add_argument(
        '-g', '--glyphs-path', metavar='GLYPHS',
        help='Path to .glyphs source file')
    xInputGroup.add_argument(
        '-u', '--ufo-paths', nargs='+', metavar='UFO',
        help='One or more paths to UFO files')
    xInputGroup.add_argument(
        '-m', '--mm-designspace', metavar='DESIGNSPACE',
        help='Path to .designspace file')

    outputGroup = parser.add_argument_group(title='Output arguments')
    outputGroup.add_argument(
        '-o', '--output', nargs='+', default=('otf', 'ttf'), metavar="FORMAT",
        help='Output font formats. Choose between: %(choices)s. '
             'Default: otf, ttf',
        choices=('ufo', 'otf', 'ttf', 'ttf-interpolatable', 'variable'))
    outputSubGroup = outputGroup.add_mutually_exclusive_group()
    outputSubGroup.add_argument(
        '--output-path', default=None,
        help="Output font file path. Only valid when the output is a single "
        "file (e.g. input is a single UFO or output is variable font)")
    outputSubGroup.add_argument(
        '--output-dir', default=None,
        help="Output folder. By default, output folders are created in the "
        "current working directory, grouping output fonts by format.")
    outputGroup.add_argument(
        '-i', '--interpolate', nargs="?", default=False, const=True,
        metavar="INSTANCE_NAME",
        help='Interpolate masters and generate all the instances defined. '
             'To only interpolate a specific instance (or instances) that '
             'match a given "name" attribute, you can pass as argument '
             'the full instance name or a regular expression. '
             'E.g.: -i "Noto Sans Bold"; or -i ".* UI Condensed". '
             '(for Glyphs or MutatorMath sources only). ')
    outputGroup.add_argument(
        '-M', '--masters-as-instances', action='store_true',
        help='Output masters as instances')
    outputGroup.add_argument(
        '--family-name',
        help='Family name to use for masters, and to filter output instances')
    outputGroup.add_argument(
        '--round-instances', dest='round_instances', action='store_true',
        help='Apply integer rounding to all geometry when interpolating')
    outputGroup.add_argument(
        '--designspace-path', default=None,
        help='Path to output designspace file (for Glyphs sources only).')
    outputGroup.add_argument(
        '--master-dir', default=None,
        help='Directory where to write master UFO. Default: "./master_ufo". '
             'If value is "{tmp}", a temporary directory is created and '
             'removed at the end (for Glyphs sources only).')
    outputGroup.add_argument(
        '--instance-dir', default=None,
        help='Directory where to write instance UFOs. Default: '
             '"./instance_ufo". If value is "{tmp}", a temporary directory '
             'is created and removed at the end (for Glyphs sources only).')
    outputGroup.add_argument(
        '--validate-ufo', action='store_true',
        help='Enable ufoLib validation on reading/writing UFO files. It is '
             'disabled by default')

    contourGroup = parser.add_argument_group(title='Handling of contours')
    contourGroup.add_argument(
        '--keep-overlaps', dest='remove_overlaps', action='store_false',
        help='Do not remove any overlap.')
    contourGroup.add_argument(
        '--overlaps-backend', dest='overlaps_backend', metavar="BACKEND",
        choices=("booleanOperations", "pathops"), default="booleanOperations",
        help='Select library to remove overlaps. Choose between: %(choices)s '
             '(default: %(default)s)')
    contourGroup.add_argument(
        '--keep-direction', dest='reverse_direction', action='store_false',
        help='Do not reverse contour direction when output is ttf or '
             'ttf-interpolatable')
    contourGroup.add_argument(
        '-e', '--conversion-error', type=float, default=None, metavar='ERROR',
        help='Maximum approximation error for cubic to quadratic conversion '
             'measured in EM')
    contourGroup.add_argument(
        '-a', '--autohint', nargs='?', const='',
        help='Run ttfautohint. Can provide arguments, quoted')
    contourGroup.add_argument(
        '--cff-round-tolerance', type=float, default=None, metavar='FLOAT',
        help='Restrict rounding of point coordinates in CFF table to only '
             'those floats whose absolute difference from their integral part '
             'is less than or equal to the tolerance. By default, all floats '
             'are rounded to integer (tolerance 0.5); 0 disables rounding.'
    )

    layoutGroup = parser.add_argument_group(title='Handling of OpenType Layout')
    layoutGroup.add_argument(
        '--interpolate-binary-layout', nargs="?", default=False, const=True,
        metavar="MASTER_DIR",
        help='Interpolate layout tables from compiled master binaries. '
             'Requires Glyphs or MutatorMath source.')
    layoutGroup.add_argument(
        "--feature-writer", metavar="CLASS", action="append",
        dest="feature_writer_specs",
        help="string specifying a feature writer class to load, either "
             "built-in or from an external module, optionally initialized with "
             "the given keyword arguments. The class and module names are "
             "separated by '::'. The option can be repeated multiple times "
             "for each writer class. A special value of 'None' will disable "
             "all automatic feature generation. The option overrides both the "
             "default ufo2ft writers and those specified in the UFO lib.")

    feaCompilerGroup = layoutGroup.add_mutually_exclusive_group(required=False)
    feaCompilerGroup.add_argument(
        '--use-afdko', action='store_true',
        help='Use makeOTF instead of feaLib to compile FEA.')
    feaCompilerGroup.add_argument(
        '--mti-source',
        help='Path to mtiLib .txt feature definitions (use instead of FEA)')

    glyphnamesGroup = parser.add_mutually_exclusive_group(required=False)
    glyphnamesGroup.add_argument(
        '--production-names', dest='use_production_names', action='store_true',
        help='Rename glyphs with production names if available otherwise use '
             'uninames.')
    glyphnamesGroup.add_argument(
        '--no-production-names', dest='use_production_names',
        action='store_false')

    subsetGroup = parser.add_mutually_exclusive_group(required=False)
    subsetGroup.add_argument(
        '--subset', dest='subset', action='store_true',
        help='Subset font using export flags set by glyphsLib')
    subsetGroup.add_argument(
        '--no-subset', dest='subset', action='store_false')

    subroutinizeGroup = parser.add_mutually_exclusive_group(required=False)
    subroutinizeGroup.add_argument(
        '-s', '--subroutinize', action='store_true',
        help='Optimize CFF table using compreffor (default)')
    subroutinizeGroup.add_argument(
        '-S', '--no-subroutinize', dest='subroutinize', action='store_false')

    parser.set_defaults(use_production_names=None, subset=None,
                        subroutinize=True)

    logGroup = parser.add_argument_group(title='Logging arguments')
    logGroup.add_argument(
        '--timing', action='store_true',
        help="Print the elapsed time for each steps")
    logGroup.add_argument(
        '--verbose', default='INFO', metavar='LEVEL',
        choices=('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'),
        help='Configure the logger verbosity level. Choose between: '
             '%(choices)s. Default: INFO')
    args = vars(parser.parse_args(args))

    specs = args.pop("feature_writer_specs")
    if specs is not None:
        args["feature_writers"] = _loadFeatureWriters(parser, specs)

    glyphs_path = args.pop('glyphs_path')
    ufo_paths = args.pop('ufo_paths')
    designspace_path = args.pop('mm_designspace')
    input_format = ("Glyphs" if glyphs_path else
                    "designspace" if designspace_path else
                    "UFO") + " source"

    if 'variable' in args['output']:
        if not (glyphs_path or designspace_path):
            parser.error(
                'Glyphs or designspace source required for variable font')
        exclude_args(parser, args,
                     ['interpolate', 'masters_as_instances',
                      'interpolate_binary_layout'],
                     "variable output")

    try:
        project = FontProject(timing=args.pop('timing'),
                              verbose=args.pop('verbose'),
                              validate_ufo=args.pop('validate_ufo'))

        if glyphs_path:
            with _make_tempdirs(parser, args):
                project.run_from_glyphs(glyphs_path, **args)
            return

        exclude_args(parser, args,
                     ['family_name', 'mti_source', 'designspace_path',
                      'master_dir', 'instance_dir'],
                     input_format)
        if designspace_path:
            project.run_from_designspace(designspace_path, **args)
            return

        exclude_args(parser, args,
                     ['interpolate', 'interpolate_binary_layout',
                      'round_instances'],
                    input_format)
        project.run_from_ufos(
            ufo_paths, is_instance=args.pop('masters_as_instances'), **args)
    except FontmakeError as e:
        import sys
        sys.exit("fontmake: error: %s" % e)


if __name__ == '__main__':
    import sys
    sys.exit(main())
