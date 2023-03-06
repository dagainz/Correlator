from io import TextIOWrapper
from typing import Dict

from Correlator.config import GlobalConfig
from Correlator.Event.core import EventListener, Event

CSVListenConfig = {
        'csv.output_directory': {
            'default': 'csv',
            'desc': 'The directory to write CSV files into'
        }
}


class CSVListener(EventListener):

    GlobalConfig.add(CSVListenConfig)

    def __init__(self):
        self.csv_files: Dict[str: TextIOWrapper] = {}

    def process_event(self, event: Event):
        if not event.is_audit:
            return

        row = event.csv_row()
        if not row:
            return

        csv_name = f'{event.system}-{event.audit_id}'
        if csv_name not in self.csv_files:
            from Correlator.util import rotate_file  # Avoid cyclic import
            rotate_file(csv_name, 'csv')
            filehandle = open(csv_name + ".csv", "w")
            self.csv_files[csv_name] = filehandle
            if filehandle.tell() == 0:
                header = event.csv_header()
                if header:
                    filehandle.write(header + '\n')
        else:
            filehandle = self.csv_files[csv_name]

        filehandle.write(row + '\n')
