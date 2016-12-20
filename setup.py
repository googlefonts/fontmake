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


from setuptools import setup, find_packages
from io import open


with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="fontmake",
    version="1.1.0.dev0",
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
    install_requires=[
        "fonttools>=3.1.2",
        "cu2qu>=1.1",
        "glyphsLib>=1.1",
        "ufo2ft>=0.2",
        "MutatorMath>=2.0",
        "defcon>=0.2",
        "booleanOperations>=0.6",
    ],
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
