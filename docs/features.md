# Persistence

Correlator has a simple facility to persist system and module data across invocations. When enabled, it will
occasionally serialize the root store and write it to a file. During startup, it initializes its root store to a 
previous state by loading and deserializing the saved store file. Correlator will also update this store file when it
cleanly exits.

Serialization is done by Python pickle, so anything that can be picked and unpickled can be used in each module's store
and will persist if persistence is enabled.

**Note**: The store contains saved state information for all enabled modules. The system assumes all modules
that are currently loaded were also loaded when the persistence store file was created. The system will not work
properly if this is not the case, and there is currently no safeguard.

The configuration parameter *syslog_server.save_store_interval* controls the amount of time between persistence store
saves.

# Scheduled 