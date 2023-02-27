# Correlator

Correlator is a prototype python library that facilitates the creation of python based event reading and
processing systems. These are used to analyze, report, and take action on system log events presumably
generated from other systems or applications.

## Build and install

To build the python package, ensure you have build installed and then run it in the project directory:

    pip install build
    python -m build

This should build a wheel file and tarball in the dist/ directory.

This file can then be installed into its own virtual environment by running pip:

    pip install path/to/Correlator-X.Y.Z-py3-none-any.whl

