from io import TextIOWrapper
from os.path import abspath, join, exists
from typing import Dict

from Correlator.global_config import ConfigType
from Correlator.Event.core import EventListener, Event, EventType
from Correlator.stack import SimpleException
from Correlator.util import listize


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
    }
]


class CSVListener(EventListener):
    """ Correlator Event handler to write Audit events as CSV file rows

    Each individual audit event gets written into a CSV file named after
    itself in the format: module_id-audit_id.csv.

    If files argument is not provided, all records from all modules will
    generate CSV data. If it is, then only generate CSV data (and resulting
    files) for the indicated files.

    e.g. 'sshd_logins-sshd_login' would result in only the sshd_login event
    dispatched from the sshd_logins module being logged.

    Args:
        files: List files of Correlator modules in this stack

    """

    """"""

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_to_config(CSVListenConfig)
        self.default_action = False

        self.csv_files: Dict[str: TextIOWrapper] = {}
        self.csv_dir = None
        self.rotate_files = True

    def initialize(self):

        self.csv_dir = abspath(self.get_config('output_directory'))
        if not exists(self.csv_dir):
            raise SimpleException(f'Path does not exist: {self.csv_dir}')
        self.rotate_files = self.get_config('rotate_files')
        self.log.debug(f'Calculated CSV path: {self.csv_dir}')

    def process_event(self, event: Event):

        fq_event_id = f'{event.system}-{event.event_id}'

        if event.type != EventType.Dataset:
            self.log.warning(f'Ignoring non Dataset type event {fq_event_id}')
            return

        row = event.csv_row()
        if not row:
            self.log.debug(f'Event produced no csv data!')
            return

        if fq_event_id not in self.csv_files:
            # We don't yet have this file open.
            full_path = join(self.csv_dir, fq_event_id)
            if self.rotate_files:
                self.log.debug(f'Rotating {full_path}.csv')
                from Correlator.util import rotate_file  # Avoid cyclic import
                rotate_file(full_path, 'csv')

            # Open new CSV file
            filehandle = open(full_path + ".csv", "a")

            # Add its handle to the list of open files
            self.csv_files[fq_event_id] = filehandle

        else:
            filehandle = self.csv_files[fq_event_id]

        # If file is at position 0, and our event provides header
        # names, write the header to the file

        if filehandle.tell() == 0:
            header = event.csv_header()
            if header:
                filehandle.write(header + '\n')

        # Write the row, and flush the output buffer

        filehandle.write(row + '\n')
        filehandle.flush()
