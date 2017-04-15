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

import sys
from setuptools import setup, find_packages, Command
from distutils import log
from io import open


class bump_version(Command):

    description = "increment the package version and commit the changes"

    user_options = [
        ("major", None, "bump the first digit, for incompatible API changes"),
        ("minor", None, "bump the second digit, for new backward-compatible features"),
        ("patch", None, "bump the third digit, for bug fixes (default)"),
    ]

    def initialize_options(self):
        self.minor = False
        self.major = False
        self.patch = False

    def finalize_options(self):
        part = None
        for attr in ("major", "minor", "patch"):
            if getattr(self, attr, False):
                if part is None:
                    part = attr
                else:
                    from distutils.errors import DistutilsOptionError
                    raise DistutilsOptionError(
                        "version part options are mutually exclusive")
        self.part = part or "patch"

    def bumpversion(self, part, **kwargs):
        """ Run bumpversion.main() with the specified arguments.
        """
        import bumpversion

        args = ['--verbose'] if self.verbose > 1 else []
        for k, v in kwargs.items():
            k = "--{}".format(k.replace("_", "-"))
            is_bool = isinstance(v, bool) and v is True
            args.extend([k] if is_bool else [k, str(v)])
        args.append(part)

        log.debug(
            "$ bumpversion %s" % " ".join(a.replace(" ", "\\ ") for a in args))

        bumpversion.main(args)

    def run(self):
        log.info("bumping '%s' version" % self.part)
        self.bumpversion(self.part)


class release(bump_version):
    """Drop the developmental release '.devN' suffix from the package version,
    open the default text $EDITOR to write release notes, commit the changes
    and generate a git tag.

    Release notes can also be set with the -m/--message option, or by reading
    from standard input.
    """

    description = "tag a new release"

    user_options = [
        ("message=", 'm', "message containing the release notes"),
    ]

    def initialize_options(self):
        self.message = None

    def finalize_options(self):
        import re

        current_version = self.distribution.metadata.get_version()
        if not re.search(r"\.dev[0-9]+", current_version):
            from distutils.errors import DistutilsSetupError
            raise DistutilsSetupError(
                "current version (%s) has no '.devN' suffix.\n       "
                "Run 'setup.py bump_version' with any of "
                "--major, --minor, --patch options" % current_version)

        message = self.message
        if message is None:
            if sys.stdin.isatty():
                # stdin is interactive, use editor to write release notes
                message = self.edit_release_notes()
            else:
                # read release notes from stdin pipe
                message = sys.stdin.read()

        if not message.strip():
            from distutils.errors import DistutilsSetupError
            raise DistutilsSetupError("release notes message is empty")

        self.message = "v{new_version}\n\n%s" % message

    @staticmethod
    def edit_release_notes():
        """Use the default text $EDITOR to write release notes.
        If $EDITOR is not set, use 'nano'."""
        from tempfile import mkstemp
        import os
        import shlex
        import subprocess

        text_editor = shlex.split(os.environ.get('EDITOR', 'nano'))

        fd, tmp = mkstemp(prefix='bumpversion-')
        try:
            os.close(fd)
            with open(tmp, 'w') as f:
                f.write("\n\n# Write release notes.\n"
                        "# Lines starting with '#' will be ignored.")
            subprocess.check_call(text_editor + [tmp])
            with open(tmp, 'r') as f:
                changes = "".join(
                    l for l in f.readlines() if not l.startswith('#'))
        finally:
            os.remove(tmp)
        return changes

    def run(self):
        log.info("stripping developmental release suffix")
        # drop '.dev0' suffix, commit with given message and create git tag
        self.bumpversion("release",
                         tag=True,
                         message="Release {new_version}",
                         tag_message=self.message)


needs_wheel = {'bdist_wheel'}.intersection(sys.argv)
wheel = ['wheel'] if needs_wheel else []
needs_bump2version = {'release', 'bump_version'}.intersection(sys.argv)
bump2version = ['bump2version'] if needs_bump2version else []

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="fontmake",
    version="1.2.4.dev0",
    description=("Compile fonts from sources (UFO, Glyphs) to binary "
                 "(OpenType, TrueType)."),
    long_description=long_description,
    url="https://github.com/googlei18n/fontmake",
    license="Apache Software License 2.0",
    packages=find_packages("Lib"),
    package_dir={'': 'Lib'},
    entry_points={
        'console_scripts': [
            'fontmake = fontmake.__main__:main'
        ]
    },
    setup_requires=wheel + bump2version,
    install_requires=[
        "fonttools>=3.10.0",
        "cu2qu>=1.1.1",
        "glyphsLib>=1.6.0",
        "ufo2ft>=0.5.0",
        "MutatorMath>=2.0.4",
        "defcon>=0.3.1",
        "booleanOperations>=0.7.0",
    ],
    cmdclass={
        "release": release,
        "bump_version": bump_version,
    },
    classifiers=[
        'Development Status :: 4 - Beta',
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
        "Topic :: Text Processing :: Fonts",
    ],
)
