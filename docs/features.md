# Features

## Persistence store

### The problem

For various reasons, most (if not all) logic modules needs to maintain data, stored in python variables, to 
represent the current
state of the system. All the included modules keep state, if for nothing more than to collect module level statistics.
Most modules that correlate and collect data from log records will also require a running state to facilitate this.

The issue is that any data stored in module variables will be lost whenever correlator stops for any reason. As an
example, the sshd module maintains a list of *transactions* that contain all of the information pertaining the
transaction. Take the case of a *valid login*. The transaction starts with that with information that gets added as log entries
associated with 
In the case of a valid login, a transaction
get created upon an initial log entry, and terminates (and dispatches an event) with one that indicates the connection
is closed. 

Without persistence, if correlator is shut down in the middle of the sequence, when it starts again it will not
correlate the later log entries with the prior, and the transaction will be lost.

### The solution

Each module instance contains a variable that operates as a module *store*. Correlator has a simple facility that, when
enabled, will use a disk file to maintain the contents of the store between invocations.

It does this by loading and deserializing a file on the filesystem into the modules state area upon startup, and
serializing the modules state area and write it to the disk file occasionally and when the system is shut down.

Serialization and deserialization is handled by Python pickle, so any data structure compatible with pickle can be used 
within the module's store, and will persist when enabled.

*NOTE: The persistence store is currently built into the syslog_server frontend and only works in this context.

### Enabling persistence.

Use the --store-file <filename> when starting the syslog_server. It would be a good idea to choose a name unique
to a particular app (for example, the app name) for the reasons explained in **Caveat** below.

### Using the store in modules

Each module is provided its own store. Rather than using python variables to maintain state
information, it is recommended to define a dataclass that contains the variables required to maintain the modules state,
and use it in the module's __init__method to define it as the state model. The variables defined in the dataclass can
then be referenced as self.store.*variable* in python.

### Example: sshd module

The sshd module can be used as an example of how to use the store. It uses it to save data related to:

- Module related statistics
- The data structures used for the state engine that identifies valid sequences of log entries.
- A dictionary that contains *transactions* that get initialized upon the first log entry of a session, and get added
to as information from additional log entries belonging to that transaction are processed.
- An instance of a class used to count log in failures over time.

The module defines and uses the store by:

- Defining the SSHDStore dataclass that contains the variables / data structures that the module needs to maintain state.
- Declare it as the store's model in the module's __init__method.
- Using the variables in the store throughout the module by referencing self.store.*variable*. 

### Caveat

The store contains saved state information for all currently enabled modules. When using persistence, correlator loads
the store from disk without checking to ensure that it was created by an instance of Correlator that was using the
same modules.

If the store was created upon startup when one set of modules was active and then run again when another set of modules
is active, the system will not work correctly.

For example, with the configuration shipped with the system:

If a new store was created when the system was started with the --app report option, and then the system restarted
using one of the sshd apps (--app sshd_report), it will not work correctly as the sshd_report store is not included 
in the saved state file.

In short, the store must get created with the same app when it is re-run. There is currently no warnings or safegaurds
regarding this behavior.

### Configuration parameters

The following configuration parameters affect the behavior of the persistence store:

| Key                               | Description                                               | Type    | Default value            |
|-----------------------------------|-----------------------------------------------------------|---------|--------------------------|
| syslog_server.save_store_interval | Time in minutes in between saves of the persistence store | Integer | 5                        |
| system.run_dir                    | Writable folder for internal files                        | String  | '/var/spool/correlator'  |

##  Credential handling using keyring

Event handlers often require the use of credentials with secrets. To avoid plain text passwords stored in configuration
files, Correlator delegates credential storage to python keyring. When correlator starts up, it queries all event
handlers that are active for the running application, for credentials that are required. If any of the credentials are
not found in the ring, Correlator will exit with a message indicating which ones are missing.

After adding the missing credentials to the ring by using a command line utility, Correlator can then start, and will
use those credentials for the event handlers.

