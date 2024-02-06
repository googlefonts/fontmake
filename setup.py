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

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()


dep_versions = {
    "attrs": ">=19",
    "fontMath": ">=0.9.3",
    "fonttools": ">=4.48.1",
    "glyphsLib": ">=6.6.3",
    "ufo2ft": ">=3.0.1",
    "ufoLib2": ">=0.16.0",
}

dep_extras = {
    "fonttools": {
        "implementation_name == 'cpython'": "ufo,lxml,unicode",
        "implementation_name != 'cpython'": "ufo,unicode",
    },
    "ufo2ft": "compreffor",
}

extras_require = {
    "pathops": ["skia-pathops>=0.3.0"],
    # this is now default; kept here for backward compatibility
    "lxml": [],
    # MutatorMath is no longer supported but a dummy extras is kept below
    # to avoid fontmake installation failing if requested
    "mutatormath": [],
    "autohint": ["ttfautohint-py>=0.5.0"],
    # For reading/writing ufoLib2's .ufo.json files (cattrs + orjson)
    "json": [f"ufoLib2[json]{dep_versions['ufoLib2']}"],
    # For compiling GPOS/GSUB using the harfbuzz repacker
    "repacker": [
        f"fonttools[{extras},repacker]{dep_versions['fonttools']}; {marker}"
        for marker, extras in dep_extras["fonttools"].items()
    ],
}
# use a special 'all' key as shorthand to includes all the extra dependencies
extras_require["all"] = sum(extras_require.values(), [])

install_requires = [
    f"{name}{version}"
    for name, version in dep_versions.items()
    if name not in dep_extras
]
for name, extras in dep_extras.items():
    if isinstance(extras, dict):
        for marker, ext in extras.items():
            install_requires.append(f"{name}[{ext}]{dep_versions[name]}; {marker}")
    elif isinstance(extras, str):
        install_requires.append(f"{name}[{extras}]{dep_versions[name]}")
    else:
        raise TypeError(type(extras))


setup(
    name="fontmake",
    use_scm_version={"write_to": "Lib/fontmake/_version.py"},
    description=(
        "Compile fonts from sources (UFO, Glyphs) to binary (OpenType, TrueType)."
    ),
    long_description=long_description,
    author="James Godfrey-kittle",
    maintainer="Cosimo Lupo",
    maintainer_email="cosimo@anthrotype.com",
    long_description_content_type="text/markdown",
    url="https://github.com/googlei18n/fontmake",
    license="Apache Software License 2.0",
    packages=find_packages("Lib"),
    package_dir={"": "Lib"},
    entry_points={"console_scripts": ["fontmake = fontmake.__main__:main"]},
    setup_requires=wheel + ["setuptools_scm"],
    python_requires=">=3.8",
    install_requires=install_requires,
    extras_require=extras_require,
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
