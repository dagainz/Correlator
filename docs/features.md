# Features

## Persistence store

When using the syslog server front end,  Correlator has a simple facility to persist system and module data across
invocations. This persistence store is manifested as a disk file. Each module is able to use its private section of the
store to maintain data structures between invocations.

When enabled, it maintains state by serializing and writing the root store to a file. During startup, correlator
initializes the root store to the previous state by loading and deserializing the saved store file. Correlator 
will write the store file periodically, as well as when it cleanly exits.

Serialization is done by Python pickle, so any data structure compatible with pickle can be used in each module's store
and will persist if persistence is enabled.

**Note**: The store contains saved state information for all enabled modules. The system assumes all modules
that are currently loaded were also loaded when the persistence store file was created. The system will not work
properly if this is not the case, and there is currently no safeguard.

### Configuration parameters

The following configuration parameters affect the behavior of the persistence store:

| Key                               | Description                                               | Type    | Default value |
|-----------------------------------|-----------------------------------------------------------|---------|---------------|
| syslog_server.save_store_interval | Time in minutes in between saves of the persistence store | Integer | 5             |

##  Credential handling using keyring

To avoid plain-text passwords for external systems in configuration files, Correlator delegates credential storage to
python keyring. When starting up, Correlator will query all event handlers for required credentials.
If any of the required credentials are not found in the ring, Correlator will exit with a message indicating which ones
are missing. After adding the missing credentials to the ring by using a command line utility, Correlator will then
start and will use those credentials in the event handlers.
