import csv
from io import TextIOWrapper, StringIO
from os.path import abspath, join, exists
from typing import Dict

from Correlator.config_store import ConfigType
from Correlator.Event.core import EventListener, Event
from Correlator.util import SimpleException, prefix_run_dir


CSVListenConfig = [
    {
        'output_directory': {
            'default': 'csv',
            'desc': 'The directory to write CSV files into',
            'type': ConfigType.STRING
        }
    },
    {
        'rotate_files': {
            'default': True,
            'desc': 'Rotate existing CSV files prior to writing new records',
            'type': ConfigType.BOOLEAN
        }
    },
    {
        'cache_filehandles': {
            'default': True,
            'desc': 'Cache filehandles for performance',
            'type': ConfigType.BOOLEAN
        }
    },
    {
        'enabled': {
            'default': True,
            'desc': 'Enable module',
            'type': ConfigType.BOOLEAN
        }
    }
]


class CSVListener(EventListener):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_to_config(CSVListenConfig)

        self.io_buffer = StringIO()
        self.csv_writer = csv.writer(self.io_buffer)

        self.csv_files: Dict[str: TextIOWrapper] = {}
        self.csv_dir = None
        self.cache_filehandles = None
        self.rotate_files = None

        self.enabled = None

    def initialize(self):

        self.csv_dir = prefix_run_dir(self.get_config('output_directory'))
        if not exists(self.csv_dir):
            raise SimpleException(f'Path does not exist: {self.csv_dir}')
        self.rotate_files = self.get_config('rotate_files')
        self.enabled = self.get_config('enabled')
        self.cache_filehandles = self.get_config('cache_filehandles')
        self.log.debug(f'Resolved CSV path: {self.csv_dir}')

    def csv_encode(self, *args):
        self.csv_writer.writerow(args)

        value = self.io_buffer.getvalue().strip("\r\n")
        self.io_buffer.seek(0)
        self.io_buffer.truncate(0)
        return value + "\n"

    def process_event(self, event: Event):

        if not self.enabled:
            self.log.debug('Module disabled via configuration')
            return

        event_id = event.fq_id
        full_path = join(self.csv_dir, event_id)

        if self.cache_filehandles and event_id not in self.csv_files:
            self.log.debug(f'Caching filehandles and do not have one for {event_id} yet')
            # We don't yet have this file open.
            if self.rotate_files:
                self.log.debug(f'Rotating {full_path}.csv')
                from Correlator.util import rotate_file  # Avoid cyclic import
                rotate_file(full_path, 'csv')

            # Open new CSV file
            filehandle = open(full_path + ".csv", "a")

            # Add its handle to the list of open files
            self.csv_files[event_id] = filehandle
        elif self.cache_filehandles:
            self.log.debug(f'Caching filehandles and we do have one for {event_id}')
            filehandle = self.csv_files[event_id]
        else:
            self.log.debug('Not caching filehandles. Opening a new file')
            filehandle = open(full_path + ".csv", "a")

        # Write header of we are at beginning of file

        if filehandle.tell() == 0:
            filehandle.write(self.csv_encode(*event.field_names))

        filehandle.write(self.csv_encode(*event.field_values))
        filehandle.flush()
