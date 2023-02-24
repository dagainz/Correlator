## Building

To build a package containing this library and utilities for installation into either the main
or a virtual environment, you must:

1) ensure that you have the python package **build** installed, installing it
with pip if not:

    pip install build

2) Build the installable package by running build in the root of the project folder:

    python -m build

3) The .whl (wheel) file in the dist/ directory is the installable package.

## Installation

The .whl file produced in the build is used to install the library and utilities into a
python environment.

To do this, activate the virtual environment (if desired) and then install
the wheel file using pip:

    pip install path/to/Correlator-X.Y.Z-py3-none-any.whl

Now the library is available to your scripts, and the command line scripts can now be
executed from a shell or command prompt.
