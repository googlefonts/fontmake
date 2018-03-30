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


from argparse import ArgumentParser, ArgumentTypeError
from fontmake import __version__
from fontmake.font_project import FontProject
from fontmake.errors import FontmakeError


class PyClassType(object):
    """ Callable object which returns a Python class defined in named module.
    It can be passed as type= argument to ArgumentParser.add_argument().
    """

    def __init__(self, class_name):
        self.class_name = class_name

    def __call__(self, module_name):
        import importlib
        import inspect

        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            raise ArgumentTypeError("No module named %r" % module_name)

        try:
            klass = getattr(mod, self.class_name)
        except AttributeError as e:
            raise ArgumentTypeError("Module %r has no attribute %r"
                                    % (module_name, self.class_name))

        if not inspect.isclass(klass):
            raise ArgumentTypeError("%r is not a class: %r"
                                    % (self.class_name, type(klass)))
        return klass


def exclude_args(parser, args, excluded_args, target):
    msg = '"%s" option invalid for %s'
    for argname in excluded_args:
        if argname not in args:
            continue
        if args[argname]:
            optname = "--%s" % argname.replace("_", "-")
            parser.error(msg % (optname, target))
        del args[argname]


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
    outputGroup.add_argument(
        '-i', '--interpolate', nargs="?", default=False, const=True,
        metavar="INSTANCE_NAME",
        help='Interpolate masters and generate all the instances defined. '
             'To only interpolate a specific instance (or instances) that '
             'match a given "name" attribute, you can pass as argument '
             'the full instance name or a regular expression. '
             'E.g.: -I "Noto Sans Bold"; or -I ".* UI Condensed". '
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
             '(for Glyphs sources only).')
    outputGroup.add_argument(
        '--instance-dir', default=None,
        help='Directory where to write instance UFOs. Default: '
             '"./instance_ufo" (for Glyphs sources only)')

    contourGroup = parser.add_argument_group(title='Handling of contours')
    contourGroup.add_argument(
        '--keep-overlaps', dest='remove_overlaps', action='store_false',
        help='Do not remove any overlap.')
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

    layoutGroup = parser.add_argument_group(title='Handling of OpenType Layout')
    layoutGroup.add_argument(
        '--interpolate-binary-layout', action='store_true',
        help='Interpolate layout tables from compiled master binaries. '
             'Requires Glyphs or MutatorMath source.')
    layoutGroup.add_argument(
        '--kern-writer-module', metavar="MODULE", dest='kern_writer_class',
        type=PyClassType('KernFeatureWriter'),
        help='Module containing a custom `KernFeatureWriter` class.')
    layoutGroup.add_argument(
        '--mark-writer-module', metavar="MODULE", dest='mark_writer_class',
        type=PyClassType('MarkFeatureWriter'),
        help='Module containing a custom `MarkFeatureWriter` class.')
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
                              verbose=args.pop('verbose'))

        if glyphs_path:
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
        parser.error(e)


if __name__ == '__main__':
    import sys
    sys.exit(main())
