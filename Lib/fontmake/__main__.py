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

import logging
import sys
from argparse import ArgumentParser, FileType
from collections import namedtuple
from contextlib import contextmanager
from textwrap import dedent

from ufo2ft import CFFOptimization
from ufo2ft.featureWriters import loadFeatureWriterFromString
from ufo2ft.filters import loadFilterFromString

from fontmake import __version__
from fontmake.errors import FontmakeError
from fontmake.font_project import INTERPOLATABLE_OUTPUTS, FontProject


def _loadPlugins(parser, specs, from_string_func, parser_error_message):
    plugins = []
    seen_ellipsis = False
    for s in specs:
        if s == "None":
            # magic value that means "don't write any features or don't apply
            # any filters!"
            return []
        elif s == "...":
            if seen_ellipsis:
                parser.error(
                    parser_error_message.format(
                        "ValueError", "'...' can only be provided once"
                    )
                )
            seen_ellipsis = True
            plugins.append(...)
            continue

        try:
            plugins.append(from_string_func(s))
        except Exception as e:
            parser.error(parser_error_message.format(type(e).__name__, e))
    return plugins


def _loadFeatureWriters(parser, specs):
    return _loadPlugins(
        parser,
        specs,
        loadFeatureWriterFromString,
        "Failed to load --feature-writer:\n  {}: {}",
    )


def _loadFilters(parser, specs):
    return _loadPlugins(
        parser, specs, loadFilterFromString, "Failed to load --filter:\n  {}: {}"
    )


def exclude_args(parser, args, excluded_args, target, positive=True):
    """Delete options that are not appropriate for a following code path; exit
    with an error if excluded options were passed in by the user.

    argparse generates a namespace with all options it knows, but not every
    attribute should be passed to all code paths (i.e. options about
    interpolation should not reach `run_from_ufos()`). This function can be run
    before entering a particular code path to clean up the kwargs passed to it.

    Exit with an error message if the user actually passed the options in.
    """
    msg = '"%s" option invalid for %s'
    for argname in excluded_args:
        if argname not in args:
            continue
        if bool(args[argname]) is positive:
            optname = "--{}{}".format(
                "" if positive else "no-", argname.replace("_", "-")
            )
            parser.error(msg % (optname, target))
        del args[argname]


_ParsedInputs = namedtuple(
    "_ParsedInputs",
    [
        "glyphs_path",
        "ufo_paths",
        "designspace_path",
        "format_name",
    ],
)


def parse_mutually_exclusive_inputs(parser, args):
    glyphs_path = args.pop("glyphs_path")
    ufo_paths = args.pop("ufo_paths") or []
    designspace_path = args.pop("mm_designspace")
    posargs = args.pop("posargs")

    # assert input -flags are already mutually exclusive via argparse
    assert sum(bool(p) for p in (glyphs_path, ufo_paths, designspace_path)) <= 1

    input_flag = (
        "g" if glyphs_path else "m" if designspace_path else "u" if ufo_paths else None
    )
    if input_flag and posargs:
        parser.error(
            f"argument -{input_flag} not allowed with positional input args: "
            f"{' '.join(posargs)}"
        )

    for filename in posargs:
        if filename.endswith(".glyphs"):
            if glyphs_path:
                parser.error("Only one *.glyphs source file is allowed")
            glyphs_path = filename
        elif filename.endswith(".designspace"):
            if designspace_path:
                parser.error("Only one *.designspace source file is allowed")
            designspace_path = filename
        elif filename.endswith(".ufo"):
            ufo_paths.append(filename)
        else:
            parser.error(f"Unknown input file extension: '{filename}'")

    count = sum(bool(p) for p in (glyphs_path, ufo_paths, designspace_path))
    if count == 0:
        parser.error("No input files specified")
    elif count > 1:
        parser.error(f"Expected 1, got {count} different types of inputs files")

    format_name = (
        "Glyphs" if glyphs_path else "designspace" if designspace_path else "UFO"
    ) + " source"

    return _ParsedInputs(
        glyphs_path,
        ufo_paths,
        designspace_path,
        format_name,
    )


@contextmanager
def _make_tempdirs(parser, args):
    output = args["output"]
    tempdirs = []
    for dirname in ("master_dir", "instance_dir"):
        if args.get(dirname) == "{tmp}":
            if "ufo" in output:
                parser.error(
                    "Can't use temporary %s directory with 'ufo' output"
                    % dirname.replace("_dir", "")
                )
            import tempfile

            td = args[dirname] = tempfile.mkdtemp(prefix=dirname + "_")
            tempdirs.append(td)

    yield tempdirs

    if tempdirs:
        import shutil

        for td in tempdirs:
            shutil.rmtree(td)


def main(args=None):
    parser = ArgumentParser()
    parser.add_argument("--version", action="version", version=__version__)
    inputGroup = parser.add_argument_group(
        title="Input arguments (flags)",
        description="The following arguments are mutually exclusive (pick only one):",
    )
    xInputGroup = inputGroup.add_mutually_exclusive_group()
    xInputGroup.add_argument(
        "-g", "--glyphs-path", metavar="GLYPHS", help="Path to .glyphs source file"
    )
    xInputGroup.add_argument(
        "-u",
        "--ufo-paths",
        nargs="+",
        metavar="UFO",
        help="One or more paths to UFO files",
    )
    xInputGroup.add_argument(
        "-m",
        "--mm-designspace",
        metavar="DESIGNSPACE",
        help="Path to .designspace file",
    )
    positionalInputs = parser.add_argument_group(
        title="Input arguments (positonal)",
        description="Alternatively, guess source format from filename extension",
    )
    positionalInputs.add_argument(
        "posargs",
        nargs="*",
        metavar="INPUTS",
        help="Either one *.designspace or *.glyphs file, or one or more *.ufo",
    )

    outputGroup = parser.add_argument_group(title="Output arguments")
    outputGroup.add_argument(
        "-o",
        "--output",
        nargs="+",
        default=("otf", "ttf"),
        metavar="FORMAT",
        help="Output font formats. Choose 1 or more from: %(choices)s. Default: otf, ttf. "
        "(No file paths).",
        choices=(
            "ufo",
            "otf",
            "otf-cff2",
            "ttf",
            "ttf-interpolatable",
            "otf-interpolatable",
            "variable",
            "variable-cff2",
        ),
    )
    outputSubGroup = outputGroup.add_mutually_exclusive_group()
    outputSubGroup.add_argument(
        "--output-path",
        default=None,
        help="Output font file path. Only valid when the output is a single "
        "file (e.g. input is a single UFO or output is a single variable font)",
    )
    outputSubGroup.add_argument(
        "--output-dir",
        default=None,
        help="Output folder. By default, output folders are created in the "
        "current working directory, grouping output fonts by format.",
    )
    outputGroup.add_argument(
        "-i",
        "--interpolate",
        nargs="?",
        default=False,
        const=True,
        metavar="INSTANCE_NAME",
        help="Interpolate masters and generate all the instances defined. "
        "To only interpolate a specific instance (or instances) that "
        'match a given "name" attribute, you can pass as argument '
        "the full instance name or a regular expression. "
        'E.g.: -i "Noto Sans Bold"; or -i ".* UI Condensed". '
        "(for Glyphs or MutatorMath sources only). ",
    )
    outputGroup.add_argument(
        "--variable-fonts",
        nargs="?",
        default=".*",
        const=True,
        metavar="VARIABLE_FONT_FILENAME",
        help=dedent(
            """\
            Filter the list of variable fonts produced from the input
            Designspace file. By default all listed variable fonts are
            generated. To generate a specific variable font (or variable fonts)
            that match a given "filename" attribute, you can pass as argument
            the full filename or a regular expression. E.g.: --variable-fonts
            "MyFontVF_WeightOnly.ttf"; or --variable-fonts
            "MyFontVFItalic_.*.ttf".
        """
        ),
    )
    outputGroup.add_argument(
        "--use-mutatormath",
        action="store_true",
        help=(
            "Use MutatorMath to generate instances (supports extrapolation and "
            "anisotropic locations)."
        ),
    )
    outputGroup.add_argument(
        "-M",
        "--masters-as-instances",
        action="store_true",
        help="Output masters as instances",
    )
    outputGroup.add_argument(
        "--family-name",
        help="Family name to use for masters, and to filter output instances",
    )
    outputGroup.add_argument(
        "--round-instances",
        dest="round_instances",
        action="store_true",
        help="Apply integer rounding to all geometry when interpolating",
    )
    outputGroup.add_argument(
        "--designspace-path",
        default=None,
        help="Path to output designspace file (for Glyphs sources only).",
    )
    outputGroup.add_argument(
        "--master-dir",
        default=None,
        help='Directory where to write master UFO. Default: "./master_ufo". '
        'If value is "{tmp}", a temporary directory is created and '
        "removed at the end (for Glyphs sources only).",
    )
    outputGroup.add_argument(
        "--instance-dir",
        default=None,
        help="Directory where to write instance UFOs. Default: "
        '"./instance_ufo". If value is "{tmp}", a temporary directory '
        "is created and removed at the end (for Glyphs sources only).",
    )
    outputGroup.add_argument(
        "--no-write-skipexportglyphs",
        action="store_false",
        dest="write_skipexportglyphs",
        help="Do not store the glyph export flags in the 'public.skipExportGlyphs' "
        "key of designspace/UFO lib, but use the old private glyph lib key "
        "'com.schriftgestaltung.Glyphs.Export' (for Glyphs sources only).",
    )
    outputGroup.add_argument(
        "--validate-ufo",
        action="store_true",
        help="Enable ufoLib validation on reading/writing UFO files. It is "
        "disabled by default",
    )
    outputGroup.add_argument(
        "--check-compatibility",
        action="store_true",
        help="Check if the source files are interpolatable. It is "
        "disabled by default, but enabled when building variable fonts "
        "or what the 'Enforce Compatibility Check' custom parameter is "
        "set on a Glyphs file",
    )
    outputGroup.add_argument(
        "--expand-features-to-instances",
        action="store_true",
        help="Resolves all include()s in the master feature file and writes "
        "the full feature file to all instance UFOs. Only valid when "
        "interpolating. Use if you share feature files of masters in "
        "external files, as instances can end up elsewhere.",
    )
    outputGroup.add_argument(
        "--no-generate-GDEF",
        dest="generate_GDEF",
        action="store_false",
        help="Do not auto-generate a GDEF table, but keep an existing one intact.",
    )

    contourGroup = parser.add_argument_group(title="Handling of contours")
    contourGroup.add_argument(
        "--keep-overlaps",
        dest="remove_overlaps",
        action="store_false",
        help="Do not remove any overlap.",
    )
    contourGroup.add_argument(
        "--overlaps-backend",
        dest="overlaps_backend",
        metavar="BACKEND",
        choices=("booleanOperations", "pathops"),
        default="booleanOperations",
        help="Select library to remove overlaps. Choose between: %(choices)s "
        "(default: %(default)s)",
    )
    contourGroup.add_argument(
        "--keep-direction",
        dest="reverse_direction",
        action="store_false",
        help="Do not reverse contour direction when output is ttf or "
        "ttf-interpolatable",
    )
    contourGroup.add_argument(
        "-e",
        "--conversion-error",
        type=float,
        default=None,
        metavar="ERROR",
        help="Maximum approximation error for cubic to quadratic conversion "
        "measured in EM",
    )
    contourGroup.add_argument(
        "-f",
        "--flatten-components",
        dest="flatten_components",
        action="store_true",
        help="Flatten nested components to single level.",
    )
    contourGroup.add_argument(
        "-a",
        "--autohint",
        nargs="?",
        const=True,  # without args means run ttfautohint with default options
        help="Run ttfautohint. Can provide arguments, quoted. By default, ttfautohint "
        "is run if the (.glyphs) source contains a 'TTFAutohint options' instance "
        "custom parameter. This option overrides that. See --no-autohint to disable.",
    )
    contourGroup.add_argument(
        "-A",
        "--no-autohint",
        dest="autohint",
        action="store_false",
        help="Do not run ttfautohint, even if source contains a 'TTFAutohint options' "
        "custom parameter",
    )
    contourGroup.add_argument(
        "--cff-round-tolerance",
        type=float,
        default=None,
        metavar="FLOAT",
        help="Restrict rounding of point coordinates in CFF table to only "
        "those floats whose absolute difference from their integral part "
        "is less than or equal to the tolerance. By default, all floats "
        "are rounded to integer (tolerance 0.5); 0 disables rounding.",
    )
    contourGroup.add_argument(
        "--optimize-cff",
        type=lambda s: CFFOptimization(int(s)),
        default=CFFOptimization.SUBROUTINIZE,
        help="0 disables all optimizations; 1 specializes the CFF charstring "
        "operators; 2 (default) also enables subroutinization",
    )
    contourGroup.add_argument(
        "--subroutinizer",
        default=None,
        choices=["compreffor", "cffsubr"],
        help="name of the library to use for compressing CFF charstrings. "
        "Choose between: %(choices)s. By default compreffor is used for CFF 1, "
        "and cffsubr for CFF2. NOTE: compreffor doesn't support CFF2.",
    )
    contourGroup.add_argument(
        "--no-optimize-gvar",
        dest="optimize_gvar",
        action="store_false",
        help="Do not perform IUP optimization on variable font's 'gvar' table. "
        "(only works with 'variable' TrueType-flavored output)",
    )
    contourGroup.add_argument(
        "--filter",
        metavar="CLASS",
        action="append",
        dest="filter_specs",
        help="string specifying a filter class to load, either "
        "built-in or from an external module, optionally initialized with "
        "the given keyword arguments. The class and module names are "
        "separated by '::'. The option can be repeated multiple times "
        "for each filter class. The option overrides the filters specified "
        "in the UFO lib. You can use an ellipsis --filter='...' to keep the "
        "latter and insert additional --filter(s), either before or after it.",
    )

    layoutGroup = parser.add_argument_group(title="Handling of OpenType Layout")
    layoutGroup.add_argument(
        "--interpolate-binary-layout",
        nargs="?",
        default=False,
        const=True,
        metavar="MASTER_DIR",
        help="Interpolate layout tables from compiled master binaries. "
        "Requires Glyphs or MutatorMath source.",
    )
    layoutGroup.add_argument(
        "--feature-writer",
        metavar="CLASS",
        action="append",
        dest="feature_writer_specs",
        help="string specifying a feature writer class to load, either "
        "built-in or from an external module, optionally initialized with "
        "the given keyword arguments. The class and module names are "
        "separated by '::'. The option can be repeated multiple times "
        "for each writer class. A special value of 'None' will disable "
        "all automatic feature generation. The option overrides both the "
        "default ufo2ft writers and those specified in the UFO lib. "
        "You can use ellipsis --feature-writer='...' to keep the latter and "
        "insert additional --feature-writer(s) either before or after those.",
    )
    layoutGroup.add_argument(
        "--debug-feature-file",
        metavar="FILE",
        type=FileType("w", encoding="utf-8"),
        default=None,
        help=(
            "Path were to dump OpenType features text to debug auto-generated "
            "features (kern, mark, mkmk, etc.)."
        ),
    )

    feaCompilerGroup = layoutGroup.add_mutually_exclusive_group(required=False)
    feaCompilerGroup.add_argument(
        "--mti-source",
        help="mtiLib feature definition .plist file path (use instead of FEA)",
    )

    glyphnamesGroup = parser.add_mutually_exclusive_group(required=False)
    glyphnamesGroup.add_argument(
        "--production-names",
        dest="use_production_names",
        action="store_true",
        help="Rename glyphs with production names if available otherwise use "
        "uninames.",
    )
    glyphnamesGroup.add_argument(
        "--no-production-names", dest="use_production_names", action="store_false"
    )

    subsetGroup = parser.add_mutually_exclusive_group(required=False)
    subsetGroup.add_argument(
        "--subset",
        dest="subset",
        action="store_true",
        help="Subset font using export flags set by glyphsLib",
    )
    subsetGroup.add_argument("--no-subset", dest="subset", action="store_false")

    subroutinizeGroup = parser.add_mutually_exclusive_group(required=False)
    subroutinizeGroup.add_argument(
        "-s",
        "--subroutinize",
        action="store_true",
        help="Optimize CFF table using compreffor (default) [DEPRECATED: use "
        "--optimize-cff option instead]",
    )
    subroutinizeGroup.add_argument(
        "-S", "--no-subroutinize", dest="subroutinize", action="store_false"
    )

    parser.set_defaults(use_production_names=None, subset=None, subroutinize=None)

    logGroup = parser.add_argument_group(title="Logging arguments")
    logGroup.add_argument(
        "--timing", action="store_true", help="Print the elapsed time for each steps"
    )
    logGroup.add_argument(
        "--verbose",
        default="INFO",
        metavar="LEVEL",
        choices=("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"),
        help="Configure the logger verbosity level. Choose between: "
        "%(choices)s. Default: INFO",
    )

    args = vars(parser.parse_args(args))

    specs = args.pop("feature_writer_specs")
    if specs is not None:
        args["feature_writers"] = _loadFeatureWriters(parser, specs)

    specs = args.pop("filter_specs")
    if specs is not None:
        args["filters"] = _loadFilters(parser, specs)

    inputs = parse_mutually_exclusive_inputs(parser, args)

    if INTERPOLATABLE_OUTPUTS.intersection(args["output"]):
        if not (inputs.glyphs_path or inputs.designspace_path):
            parser.error("Glyphs or designspace source required for variable font")
        exclude_args(
            parser,
            args,
            [
                "interpolate",
                "masters_as_instances",
                "interpolate_binary_layout",
                "use_mutatormath",
            ],
            "variable output",
        )
    else:
        exclude_args(
            parser,
            args,
            ["variable_fonts", "optimize_gvar"],
            "static output",
            positive=False,
        )

    if args.get("use_mutatormath"):
        for module in ("defcon", "mutatorMath"):
            try:
                __import__(module)
            except ImportError:
                parser.error(
                    f"{module} module not found; reinstall fontmake with the "
                    "[mutatormath] extra"
                )

    PRINT_TRACEBACK = args.get("verbose", "INFO") == "DEBUG"
    try:
        project = FontProject(
            timing=args.pop("timing"),
            verbose=args.pop("verbose"),
            validate_ufo=args.pop("validate_ufo"),
        )

        if inputs.glyphs_path:
            with _make_tempdirs(parser, args):
                project.run_from_glyphs(inputs.glyphs_path, **args)
            return

        exclude_args(
            parser,
            args,
            [
                "family_name",
                "mti_source",
                "designspace_path",
                "master_dir",
                "instance_dir",
            ],
            inputs.format_name,
        )
        exclude_args(
            parser, args, ["write_skipexportglyphs"], inputs.format_name, positive=False
        )
        if inputs.designspace_path:
            project.run_from_designspace(inputs.designspace_path, **args)
            return

        exclude_args(
            parser,
            args,
            [
                "interpolate",
                "variable_fonts",
                "use_mutatormath",
                "interpolate_binary_layout",
                "round_instances",
                "expand_features_to_instances",
                "check_compatibility",
            ],
            inputs.format_name,
        )
        project.run_from_ufos(
            inputs.ufo_paths, is_instance=args.pop("masters_as_instances"), **args
        )
    except FontmakeError as e:
        if PRINT_TRACEBACK:
            logging.exception(e)
            sys.exit(1)
        sys.exit(f"fontmake: Error: {str(e)}")
    finally:
        debug_feature_file = args.get("debug_feature_file")
        if debug_feature_file is not None:
            debug_feature_file.close()


if __name__ == "__main__":
    sys.exit(main())
