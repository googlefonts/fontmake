|Travis Build Status| |Python Versions| |PyPI Version|

fontmake
========

This library provides a wrapper for several other Python libraries which
together compile fonts from various sources (.glyphs, .ufo) into
binaries (.otf, .ttf).


Installation
~~~~~~~~~~~~

Fontmake requires Python 2.7, 3.5 or later.

There are three ways of getting fontmake.

Installing from PyPI
--------------------

The standard route recommended for most people. Releases are available on
`PyPI`_ and can be installed with `pip`_. In these instructions, we install
fontmake in a virtual environment to avoid software clashes and permission
problems. Open a terminal and follow along:

.. code:: bash

    # This assumes you have Python installed. If you are unsure, get Python 3
    # from www.python.org.

    # First, go to your project folder.

    # Then, create a new virtual environment. You only need to do this the first
    # time or if you deleted the old one.
    # If you are using Python 2:
    python -m virtualenv venv
    # Otherwise, if you are using Python 3 on Mac or Linux:
    python3 -m venv venv
    # Otherwise, if you are using Python 3 on Windows:
    py -3 -m venv venv

    # Note that if you use Git to manage your project, you should add the line
    # "venv" to the text file ".gitignore". Create the file in the top directory
    # of your project if it doesn't exist. This will prevent accidentally
    # committing the entire venv to Git, which is most probably not what you want.

    # Activate the virtual environment. You need to do this every time you open
    # a new terminal.
    # On Mac or Linux, with the standard Bash shell:
    . venv/bin/activate
    # On Windows, with a cmd.exe terminal
    .\venv\Scripts\activate.bat
    # On Windows, in Powershell:
    .\venv\Scripts\Activate.ps1

    # Install fontmake.
    pip install fontmake

Use the ``-U``, ``--upgrade`` option to update fontmake and its dependencies
to the newest available release:

.. code:: bash

    # Activate virtual environment as above.

    pip install --upgrade fontmake

Using the stand-alone application
---------------------------------

If you have Python 3.6 or later installed, you can get a zip file with a
stand-alone fontmake application from the [GitHub release page]_.

1. Pick one for your platform and Python version, a "32" in the name needs a
   32-bit Python installation, a "64" a 64-bit one. If you are unsure, better
   follow the PyPI route above instead.
2. Unzip it to where you want it, e.g. your project folder.
3. Open a terminal and go to that folder.
4. On Windows, run ``python fontmake.pyz``, on other platforms run
   ``python3 fontmake.pyz``. If you see a message telling you about the options
   of fontmake, it works correctly.
5. Now follow the usage description below, but instead of running the command
   with ``fontmake``, run it with ``python fontmake.pyz`` or
   ``python3 fontmake.pyz``.

Installing from Git or source
-----------------------------

You can install the newest development code, e.g. if you want to test it:

.. code:: bash

    # Create and/or activate virtual environment as in the PyPI instructions above.

    pip install git+https://github.com/googlei18n/fontmake

Developers who want to quickly test changes to the source code without
re-installing, can use the ``--editable`` option when installing from a local
source checkout:

.. code:: bash

    # Create and/or activate virtual environment as in the PyPI instructions above.

    git clone https://github.com/googlei18n/fontmake
    cd fontmake
    pip install -e .

Usage
~~~~~

After installation, you can use the ``fontmake`` console script. For example:

.. code:: bash

    # Generate (interpolated) instance TTFs from a Glyphs.app source file.
    fontmake -g MyFont.glyphs -i -o ttf

Use ``fontmake -h`` to see options for specifying different types of input and
output.

You can also use fontmake as a module to run intermediate steps in the build
process, via methods of the ``fontmake.font_project.FontProject`` class.

.. _virtualenv: https://virtualenv.pypa.io
.. _venv: https://docs.python.org/3/library/venv.html
.. _pip: https://pip.pypa.io
.. _pip documentation: https://pip.readthedocs.io/en/stable/user_guide/#requirements-files
.. _PyPI: https://pypi.org/project/fontmake
.. _GitHub release page: https://github.com/googlei18n/fontmake/releases
.. |Travis Build Status| image:: https://travis-ci.org/googlei18n/fontmake.svg
   :target: https://travis-ci.org/googlei18n/fontmake
.. |Python Versions| image:: https://img.shields.io/badge/python-2.7%2C%203.6-blue.svg
.. |PyPI Version| image:: https://img.shields.io/pypi/v/fontmake.svg
   :target: https://pypi.org/project/fontmake/
