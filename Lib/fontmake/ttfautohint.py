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


import shutil
import subprocess
import sys
from typing import List, Optional

from fontmake.errors import FontmakeError, TTFAError


def _which_ttfautohint() -> Optional[List[str]]:
    # First check if ttfautohint-py is installed, else try to find the standalone
    # ttfautohint command-line tool, or None if neither is found.
    try:
        import ttfautohint  # noqa: F401
    except ImportError:
        ttfautohint_path = shutil.which("ttfautohint")
        return [ttfautohint_path] if ttfautohint_path else None
    else:
        return [sys.executable, "-m", "ttfautohint"]


def ttfautohint(in_file, out_file, args=None, **kwargs):
    """Thin wrapper around the ttfautohint command line tool.

    Can take in command line arguments directly as a string, or spelled out as
    Python keyword arguments.
    """

    file_args = [in_file, out_file]

    ttfautohint = _which_ttfautohint()
    if ttfautohint is None:
        raise FontmakeError(
            "ttfautohint not found; try `pip install ttfautohint-py`", in_file
        )

    if args is not None:
        if kwargs:
            raise TypeError("Should not provide both cmd args and kwargs.")
        try:
            rv = subprocess.call(ttfautohint + args.split() + file_args)
        except OSError as e:
            raise FontmakeError(
                "Could not launch ttfautohint (is it installed?)", in_file
            ) from e
        if rv != 0:
            raise TTFAError(rv, in_file)
        return

    boolean_options = (
        "debug",
        "composites",
        "dehint",
        "help",
        "ignore_restrictions",
        "detailed_info",
        "no_info",
        "adjust_subglyphs",
        "symbol",
        "ttfa_table",
        "verbose",
        "version",
        "windows_compatibility",
    )
    other_options = (
        "default_script",
        "fallback_script",
        "family_suffix",
        "hinting_limit",
        "fallback_stem_width",
        "hinting_range_min",
        "control_file",
        "hinting_range_max",
        "strong_stem_width",
        "increase_x_height",
        "x_height_snapping_exceptions",
    )

    arg_list = []
    for option in boolean_options:
        if kwargs.pop(option, False):
            arg_list.append("--" + option.replace("_", "-"))

    for option in other_options:
        arg = kwargs.pop(option, None)
        if arg is not None:
            arg_list.append("--{}={}".format(option.replace("_", "-"), arg))

    if kwargs:
        raise TypeError("Unexpected argument(s): " + ", ".join(kwargs.keys()))

    rv = subprocess.call(ttfautohint + arg_list + file_args)
    if rv != 0:
        raise TTFAError(rv, in_file)
