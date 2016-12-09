[![Travis Build Status](https://travis-ci.org/googlei18n/fontmake.svg)](https://travis-ci.org/googlei18n/fontmake)

# fontmake

This library provides a wrapper for several other Python libraries which together compile fonts from various sources (.glyphs, .ufo) into binaries (.otf, .ttf)

### Initial Installation

First, create new virtual environment. 
This is optional, but **recommended**:

To install from source:

```bash
python -m pip install --user virtualenv;  # install virtualenv if not available
python -m virtualenv env;  # create environment named 'env' in current folder
source env/bin/activate;  # activate the environment (run `deactivate` to exit)
git clone git@github.com:googlei18n/fontmake.git; # download the repo
cd fontmake;
pip install -r requirements.txt; # Install fontmake's dependencies:
pip install -e . ; # Install fontmake in "editable" mode, useful for developers
```

Alternativelu, to install from the latest release:

    pip install -U fontmake

### Usage

After installation, fontmake can be run end-to-end as a module:

```bash
source env/bin/activate # activate the environment (run `deactivate` to exit)
fontmake -g MyFont.glyphs # outputs binary font files for masters only
fontmake -h # see options for specifying different types of input and output
```

You can also use fontmake to run intermediate steps in the build process, via methods of the `fontmake.font_project.FontProject` class.

### Updating 

To update the program the process is similar to initial installation, but there are a few minor differences. 

To upgrade an installation from source:

```bash
source env/bin/activate  # activate the environment (run `deactivate` to exit)
cd fontmake;
git pull;
pip install --upgrade -r requirements.txt; # Upgrade fontmake dependencies
```

To upgrade an installation from release package:

    pip install --upgrade fontmake
