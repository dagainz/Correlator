from Correlator.Event.core import EventListener, Event, log, EventSeverity
from Correlator.config_store import ConfigType

LogConfig = [
    {
        'sample': {
            'default': '',
            'desc': 'Sample Arg no-op',
            'type': ConfigType.STRING
        }
    }
]


class LogbackListener(EventListener):

    handler_name = 'Logback'

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_to_config(LogConfig)

    def initialize(self):
        self.log.debug('Handler initialize')

    def process_event(self, event: Event):
        message = f'[{event.system} :: {event.id}] {event.summary}'
        # message = f'{event.system}: {event.summary}'
        if event.severity == EventSeverity.Error:
            self.log.error(message)
        elif event.severity == EventSeverity.Warning:
            self.log.warning(message)
        else:   # notice
            self.log.info(message)
