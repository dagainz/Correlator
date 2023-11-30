# Quickstart

## Build and install the package in a linux container on a system running Docker:

This process:
- Creates the network *correlator-net* to ease network access from application server
containers to test and validate proper operation.
- Exposes TCP port 514 in the container to port 5140 on the network
- Creates a local volume for data persistence

    git checkout https://github.com/tim-pushor/Correlator.git
    cd Correlator
    docker build -t correlator .
    docker network create correlator-net
    docker run --name correlator --net correlator-net -it -v /Users/timp/Projects/Correlator/docker-data:/var/correlator correlator

This will expose a bash prompt where you may run the CLI recipes on this page.
 
## Build and install the package directly on a unix like system:

This process details installing the python package in-place into a new python virtual environment. For more
information about in-place installs, see
[pip editable installs](https://pip.pypa.io/en/stable/topics/local-project-installs/#editable-installs "Title").

### Checkout and build

Note: Pip must be upgraded if it is < 21.3

    git checkout https://github.com/tim-pushor/Correlator.git
    cd Correlator
    python -m venv venv
    .venv/bin/activate
    pip install --upgrade pip
    pip install build
    python -m build

### Install it in-place

    pip install -e .

After the library is installed by pip you may run the CLI recipes on this page within the virtual environment.

## CLI Recipes

### Report a summary of the records in a capture file (using syslog_server)
This will process a capture file and take no action other than reporting a summary of each syslog message to the
console.

    syslog_server --read-file data/sshd-1.cap

### Run syslog server with sshd logic module with a capture file as input
This will process a capture file using the sshd logic module. It will:

- Dispatch events for both successful and failed ssh logins and attempts. 
- Dispatch a custom lockout event if a host has had more than 5 failed password attempts in the past 5 minutes.
- Collect and report statistics on these events
    
<!-- -->

    syslog_server --read-file data/sshd-1.cap --sshd

### Run syslog server on the network, reporting on syslog messages received
Run a server on port 514 (overridable with --port). Take no action other than reporting a summary of each syslog
message received to the console.

    syslog_server [--port x]

### Record syslog messages to a capture file
Run a server on port 514 (overridable with --port). Take no action other than reporting a summary of each syslog
message received on the console, and also write each record received to a capture file.

    syslog_server [--port x] --write-file

### Report a summary of the records in a capture file (using caputil)
Although performs identically to syslog_server --read-file, that behavior is not guaranteed to remain. captuil should
be used to read and write capture files.

    caputil --in capture.cap

### Create a new capture file from a subset of records in an existing one.
This can be used to create individual capture files for tests that contain only the records necessary for the test.
For example, the sshd-1.cap file included with this package was created by the following process:

- Dump the summary of the packets into a text file
- Edit the text file and mark the records to be included in the output file
- Write the output file using the capture file and text file from the last step.

<!-- -->

    caputil --in oldfile.cap > oldfile_list
    edit oldfile_list and add a hash mark (#) in front of any line that you do not want in the output file
    caputil --in oldfile.cap --out newfile.cap --record oldfile_list

