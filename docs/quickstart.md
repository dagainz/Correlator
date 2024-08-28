# Quickstart

Using Docker has advantages over installing Correlator more traditionally directly onto a computer system. Containers
provide a consistent environment for the application as well as features to help deploy, upgrade, and rolling back
deployed containers if necessary. Docker is not necessary; It is possible to use Correlator by installing it onto a Unix
like system in a Python virtual environment. Note however, the usage examples on this page (as written) are meant to be
run in the interactive docker container.

## The Docker image

The docker image must be built using the included dockerfile. Containers based on this image have the following
features and limitations:

- Entrypoint provided for both interactive and non-interactive use
- Support for configuration, the persistence store, and syslog record/packet capture files on a bind-mount or docker volume
- Correlator currently uses Python keyring to handle managing any credentials needed for event handlers. Inside docker
  containers, an *encrypted file* keyring backend is used to create an encrypted file based store. Currently, the
  encryption password must be entered every time the container is restarted, or it can be supplied as an environment 
  variable by docker run. Neither are great options.

### A note about static files.

Change written to the filesystem of the container do not normally persist when the container is stopped. Many files
(such as the configuration) are meant to persist. To address this, files meant to persist are located within the
/var/correlator directory inside the container. This directory is meant to be mounted to a docker volume or bind mounted
to a folder, which will provide persistence.

### Cloning the repo and building the docker image

    git clone https://github.com/tim-pushor/Correlator.git
    cd Correlator
    git checkout 0.0.4-RELEASE
    docker build -t correlator

### Create docker network

Creating a docker network for the container to run within helps with access from other containers, such as the
OpenSSH test container mentioned in some of the recipes on this page.

    docker network create correlator-net

### Running an interactive container

An interactive Correlator container executes in a mode appropriate for interacting with it from a command line, such as when 
testing, developing, or evaluating the software. When the container is run, it displays a banner of text with some
usage help, and then drops to a bash prompt where the syslog server (or any other scripts or utility programs) may be
run with any arguments.  The examples shown on this page all use the interactive container.

The alternative to an interactive container is a container that executes Correlator with a fixed set of command line
arguments meant to start Correlator the same way, every time. This allows for a consistent using restart policies to restart stopped
containers (among other things).

Note: Change /path/to/volume in this example to a prepared empty directory on your system. After the first run of the
container, this area will contain files.

    docker run --name correlator --net correlator-net --rm -it -p 5140:5140/tcp --mount type=bind,source=/path/to/volume,target=/var/correlator correlator

If this was successful, you will notice some help text and a bash prompt that looks similar to:

    root@4803ef622291:/usr/src/app# 

Note that the -rm argument to docker run. This instructs Docker to destroy the container when it exits. The docker run
command will need to be reissued to run the container again.

## Usage examples

### Run the syslog server on the network, reporting on syslog messages received

Run the interactive Correlator container to display the help banner and offer a bash command prompt. At the prompt
Run a server on port 514 (overridable with --port). Take no action other than reporting a summary of each syslog
message received to the console.

    syslog_server [--port x]

### Testing Correlator's OpenSSH module with another container running OpenSSH

To test or evaluate the Correlator OpenSSH module, a separate Dockerfile is provided that can be used to built and run
another container that:

- Creates a test linux user
- Runs rsyslog, configured to forward all syslog events to the Correlator container via TCP.
- Runs the OpenSSH daemon

To set up this test/demonstration, a Correlator docker image must be built, and the correlator-net docker network
created as described near the beginning of this document.

#### Building the OpenSSH docker image

    cd /path/to/correlator_repo/test/ssh
    docker build -t openssh .
    
#### Run an appropriate Correlator app and wait for connection

    docker run --name correlator --net correlator-net --rm -it -p 5140:5140/tcp --mount type=bind,source=/path/to/volume,target=/var/correlator correlator

Then at the containers bash prompt:

    syslog_server --app ssh-report

This starts the syslog server and waits for a TCP syslog connection on the network. Log records are processed
using the OpenSSH Correlator module, and any events dispatched by the module are simply reported (to stdout, which
also ends up the Docker log for the container.

#### Run the OpenSSH docker container

Keep the shell that is running the syslog_server open and viewable and start a new shell to run the new container.

    docker run --name openssh --net correlator-net --rm -p 2222:22 openssh

- This will start the second container reporting on its operation to stdout.
- port 2222 on the Docker host will be mapped to port 22 in the container

At this point the output from the Correlator container should indicate that a TCP connection from the OpenSSH container
has been established with a message like **Connection from: <addr>:<port>**. You should also be able to attempt an ssh
connection to port 2222 of the docker host. For the first test, choose a username that does not exist in the container,
such as *noone*.

    ssh -p 2222 noone@localhost 

The ssh client should prompt to enter a password for noone@localhost. Enter any password, 3 times so the ssh server
fails with too many attempts.

Correlator should detect this and respond with an event, that is visible in the containers output, similar to:

2024-04-25 14:37:15 Logback-handler ERROR: \[OpenSSH :: SSHDLoginFailed] User xxxx from host yyy.yyy.yyy.yyy failed to login after 3 failures

Some other things to try:

- Log in using the test user specified in the OpenSSH containers Dockerfile (testuy/testpass if it wasn't changed). Note
that the event will not get generated until you close the ssh connection.
- Configure the container and your docker host to use encryption keys rather than passwords. Attempt the success case
of logging in using your private key. Maybe also the failure case of using the wrong key.
- Try spamming the ssh server with invalid login requests for different users (at least 5 times). for example:

    ssh -p 2222 test1@localhost
    ... repeat with test2@localhost, test3@localhost, test4@localhost
    ssh -p 2222 test5@localhost


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

