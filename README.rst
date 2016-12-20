|Travis Build Status|

fontmake
========

This library provides a wrapper for several other Python libraries which
together compile fonts from various sources (.glyphs, .ufo) into
binaries (.otf, .ttf).

Install
~~~~~~~

Create new virtual environment (optional, but *recommended*):

.. code:: bash

    python -m pip install --user virtualenv  # install virtualenv if not available
    python -m virtualenv env  # create environment named 'env' in current folder
    source env/bin/activate  # activate the environment (run `deactivate` to exit)

Install fontmake's dependencies:

.. code:: bash

    pip install -r requirements.txt

Install fontmake:

.. code:: bash

    pip install -e .  # `-e` is for "editable" mode, only required for developers

Run
~~~

After installation, fontmake can be run end-to-end as a module:

.. code:: bash

    # outputs master binaries
    fontmake -g MyFont.glyphs

Use ``-h`` to see options for specifying different types of input and
output.

You can also use fontmake to run intermediate steps in the build
process, via methods of the ``fontmake.font_project.FontProject`` class.

.. |Travis Build Status| image:: https://travis-ci.org/googlei18n/fontmake.svg
   :target: https://travis-ci.org/googlei18n/fontmake
