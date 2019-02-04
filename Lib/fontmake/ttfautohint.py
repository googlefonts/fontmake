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


import subprocess

from fontmake.errors import TTFAError


def ttfautohint(in_file, out_file, args=None, **kwargs):
    """Thin wrapper around the ttfautohint command line tool.

    Can take in command line arguments directly as a string, or spelled out as
    Python keyword arguments.
    """

    arg_list = ["ttfautohint"]
    file_args = [in_file, out_file]

    if args is not None:
        if kwargs:
            raise TypeError("Should not provide both cmd args and kwargs.")
        rv = subprocess.call(arg_list + args.split() + file_args)
        if rv != 0:
            raise TTFAError(rv)
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

    for option in boolean_options:
        if kwargs.pop(option, False):
            arg_list.append("--" + option.replace("_", "-"))

    for option in other_options:
        arg = kwargs.pop(option, None)
        if arg is not None:
            arg_list.append("--{}={}".format(option.replace("_", "-"), arg))

    if kwargs:
        raise TypeError("Unexpected argument(s): " + ", ".join(kwargs.keys()))

    rv = subprocess.call(arg_list + file_args)
    if rv != 0:
        raise TTFAError(rv)
