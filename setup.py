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
from setuptools import setup, find_packages
from io import open


needs_wheel = {'bdist_wheel'}.intersection(sys.argv)
wheel = ['wheel'] if needs_wheel else []

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="fontmake",
    use_scm_version={"write_to": "Lib/fontmake/_version.py"},
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
        ],
    },
    setup_requires=wheel + ["setuptools_scm"],
    install_requires=[
        "fonttools>=3.30.0",
        "cu2qu>=1.5.0",
        "glyphsLib>=3.1.2",
        "ufo2ft>=2.4.0",
        "MutatorMath>=2.1.1",
        "defcon>=0.5.3",
        "booleanOperations>=0.8.0",
        "ufoLib[lxml]>=2.3.1",
    ],
    extras_require={
        "pathops": [
            "skia-pathops>=0.2.0",
        ],
        # this is now default; kept here for backward compatibility
        "lxml": [
            # "lxml>=4.2.4",
        ],
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
