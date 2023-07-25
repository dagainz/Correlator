from Correlator.Event.core import EventListener, Event, log, EventStatus


class LogbackListener(EventListener):

    handler_name = 'Logback'

    def initialize(self):
        self.log.debug('Handler initialize')

    def process_event(self, event: Event):
        if event.status == EventStatus.Error:
            self.log.error(f'{event.system}: {event.summary}')
        elif event.status == EventStatus.Warning:
            self.log.warning(f'{event.system}: {event.summary}')
        else:   # notice
            self.log.info(f'{event.system}: {event.summary}')
