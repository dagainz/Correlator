from Correlator.Event.core import EventListener, Event, log, EventSeverity


class LogbackListener(EventListener):

    handler_name = 'Logback'

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
