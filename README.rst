|Travis Build Status| |Python Versions| |PyPI Version|

fontmake
========

This library provides a wrapper for several other Python libraries which
together compile fonts from various sources (.glyphs, .ufo) into
binaries (.otf, .ttf).


Installation
~~~~~~~~~~~~

Fontmake requires Python 2.7, 3.5 or later.

Releases are available on `PyPI`_ and can be installed with `pip`_.

.. code:: bash

    pip install fontmake

Use the ``-U``, ``--upgrade`` option to update fontmake and its dependencies
to the newest available release:

.. code:: bash

    pip install -U fontmake

Alternatively, you can download the git repository and install from source:

.. code:: bash

    git clone https://github.com/googlei18n/fontmake
    cd fontmake
    pip install .

Developers who want to quickly test changes to the source code without
re-installing, can use the "--editable" option when installing from a local
source checkout:

.. code:: bash

    pip install -e .

However, even with an editable installation, it is recommended to always
reinstall fontmake after pulling the latest changes from the upstream repo:

.. code:: bash

    git pull
    pip install -e .

This makes sure that the requirements are still met, i.e. updating old ones
to new minimum required versions, or installing new ones as needed.

It also ensures that the package metadata is updated, e.g. when displaying the
installed version with ``pip list`` or ``pip show fontmake``.


Virtual environments
--------------------

It is recommended to install fontmake inside a "virtual environment" to prevent
conflicts between its dependencies and other modules installed globally.

You can either install `virtualenv`_ (``pip install --user virtualenv``), or
use the Python 3 `venv`_ module.

- To create a new virtual environment, e.g. inside the 'env' directory:

  .. code:: bash

      python -m virtualenv env

  Similarly, if you are using the ``venv`` module:

  .. code:: bash

      python3 -m venv env

- To "activate" a virtual environment, i.e. temporarily place the folder
  containing the executable scripts on the shell's ``$PATH`` so they can be
  run from anywhere, run this from the Bash shell (e.g., Linux, Mac):

  .. code:: bash

      source env/bin/activate

  If you are using the Windows Command Prompt:

  .. code:: bash

      env/bin/activate.bat

- To deactivate the virtual environment and restore the original environment,
  just do:

  .. code:: bash

      deactivate


Dependencies and requirements files
-----------------------------------

Fontmake is mostly the front-end interface for a number of Python libraries.

These are automatically installed or updated to the minimum required version
whenever you install a given fontmake version.

Pip also allows to specify a set of packages that work together in text files.
These can be used with the ``-r`` option to recreate a particular environment.

There are two such requirements files in fontmake repository:

- ``dev_requirements.txt``: contains the URLs of the git repositories for
  all fontmake's dependencies.

- ``requirements.txt``: contains the current released versions of the direct
  dependencies which fontmake is tested against.

To install from the latest development versions, or upgrade an existing
environment to the current ``HEAD`` commit of the respective ``master``
branches, you can do:

.. code:: bash

    pip install -r dev_requirements.txt

For more information on requirements files, see `pip documentation`_.


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
.. |Travis Build Status| image:: https://travis-ci.org/googlei18n/fontmake.svg
   :target: https://travis-ci.org/googlei18n/fontmake
.. |Python Versions| image:: https://img.shields.io/badge/python-2.7%2C%203.6-blue.svg
.. |PyPI Version| image:: https://img.shields.io/pypi/v/fontmake.svg
   :target: https://pypi.org/project/fontmake/
