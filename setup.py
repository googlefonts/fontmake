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

import site
import sys
from io import open

from setuptools import find_packages, setup

# See https://github.com/pypa/pip/issues/7953
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

needs_wheel = {"bdist_wheel"}.intersection(sys.argv)
wheel = ["wheel"] if needs_wheel else []

with open("README.rst", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="fontmake",
    use_scm_version={"write_to": "Lib/fontmake/_version.py"},
    description=(
        "Compile fonts from sources (UFO, Glyphs) to binary (OpenType, TrueType)."
    ),
    long_description=long_description,
    url="https://github.com/googlei18n/fontmake",
    license="Apache Software License 2.0",
    packages=find_packages("Lib"),
    package_dir={"": "Lib"},
    entry_points={"console_scripts": ["fontmake = fontmake.__main__:main"]},
    setup_requires=wheel + ["setuptools_scm"],
    python_requires=">=3.6",
    install_requires=[
        "fonttools[ufo,lxml,unicode]>=4.21.1 ; platform_python_implementation == 'CPython'",
        "fonttools[ufo,unicode]>=4.21.1 ; platform_python_implementation != 'CPython'",
        "glyphsLib>=5.3.2",
        "ufo2ft[compreffor]>=2.20.0",
        "fontMath>=0.6.0",
        "ufoLib2>=0.8.0",
        "attrs>=19",
    ],
    extras_require={
        "pathops": ["skia-pathops>=0.3.0"],
        # this is now default; kept here for backward compatibility
        "lxml": [
            # "lxml>=4.2.4",
        ],
        "mutatormath": ["MutatorMath>=2.1.2"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Topic :: Multimedia :: Graphics",
        "Topic :: Multimedia :: Graphics :: Graphics Conversion",
        "Topic :: Multimedia :: Graphics :: Editors :: Vector-Based",
        "Topic :: Text Processing :: Fonts",
    ],
)
