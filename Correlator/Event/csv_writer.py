from io import TextIOWrapper
from os.path import abspath, join
from typing import Dict
import logging


from Correlator.config import GlobalConfig, ConfigType
from Correlator.Event.core import EventListener, Event
from Correlator.util import listize

log = logging.getLogger(__name__)


CSVListenConfig = {
        'csv.output_directory': {
            'default': 'csv',
            'desc': 'The directory to write CSV files into',
            'type': ConfigType.INTEGER
        }
}


class CSVListener(EventListener):

    GlobalConfig.add(CSVListenConfig)

    def __init__(self, files=None):
        self.csv_files: Dict[str: TextIOWrapper] = {}
        self.write_files = set()

        if files:
            for file in listize(files):
                self.write_files.add(file)

        self.csv_dir = abspath(GlobalConfig.get('csv.output_directory'))
        log.debug(f'Calculated CSV path: {self.csv_dir}')

    def process_event(self, event: Event):
        if not event.is_audit:
            return

        row = event.csv_row()
        if not row:
            return

        csv_name = f'{event.system}-{event.audit_id}'
        if self.write_files and csv_name not in self.write_files:
            log.debug("Not interested in event")
            # We aren't interested.
            return

        if csv_name not in self.csv_files:
            full_path = join(self.csv_dir, csv_name)
            from Correlator.util import rotate_file  # Avoid cyclic import
            rotate_file(full_path, 'csv')
            filehandle = open(full_path + ".csv", "w")
            self.csv_files[csv_name] = filehandle
            if filehandle.tell() == 0:
                header = event.csv_header()
                if header:
                    filehandle.write(header + '\n')
        else:
            filehandle = self.csv_files[csv_name]

        filehandle.write(row + '\n')
        filehandle.flush()
