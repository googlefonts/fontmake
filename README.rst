|GitHub Actions Build Status| |Python Versions| |PyPI Version|

fontmake
========

This library provides a wrapper for several other Python libraries which
together compile fonts from various sources (.glyphs, .ufo) into
binaries (.otf, .ttf).


Installation
~~~~~~~~~~~~

Fontmake requires Python 3.6 or later.

Releases are available on `PyPI`_ and can be installed with `pip`_.

.. code:: bash

    pip install fontmake

Use the ``-U``, ``--upgrade`` option to update fontmake and its dependencies
to the newest available release:

.. code:: bash

    pip install -U fontmake

Alternatively, you can download the git repository and install from source:

.. code:: bash

    git clone https://github.com/googlefonts/fontmake
    cd fontmake
    pip install .

Developers who want to quickly test changes to the source code without
re-installing, can use the "--editable" option when installing from a local
source checkout:

.. code:: bash

    pip install -e .

It is recommended to install fontmake inside a "virtual environment" to prevent
conflicts between its dependencies and other modules installed globally.

You could also use the `pipx`_ tool to automate the installation/upgrade of
python apps like fontmake in isolated environments.

Usage
~~~~~

After installation, you can use the ``fontmake`` console script. For example:

.. code:: bash

    fontmake -g MyFont.glyphs  # outputs binary font files for masters only

Use ``fontmake -h`` to see options for specifying different types of input and
output.

You can also use fontmake as a module to run intermediate steps in the build
process, via methods of the ``fontmake.font_project.FontProject`` class.

.. _virtualenv: https://virtualenv.pypa.io
.. _venv: https://docs.python.org/3/library/venv.html
.. _pip: https://pip.pypa.io
.. _pip documentation: https://pip.readthedocs.io/en/stable/user_guide/#requirements-files
.. _PyPI: https://pypi.org/project/fontmake
.. _Github releases: https://github.com/googlefonts/fontmake/releases
.. _pipx: https://github.com/pipxproject/pipx
.. |GitHub Actions Build Status| image:: https://github.com/googlefonts/fontmake/workflows/Test%20+%20Deploy/badge.svg
.. |Python Versions| image:: https://img.shields.io/badge/python-3.6-blue.svg
.. |PyPI Version| image:: https://img.shields.io/pypi/v/fontmake.svg
   :target: https://pypi.org/project/fontmake/
