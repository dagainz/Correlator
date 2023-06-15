from Correlator.Event.core import EventListener, Event, log, EventStatus


class LogbackListener(EventListener):

    name = 'Logback'

    def __init__(self):
        # todo: Why?
        pass

    def process_event(self, event: Event):
        if event.status == EventStatus.Error:
            log.error(f'{event.system}: {event.summary}')
        elif event.status == EventStatus.Warning:
            log.warning(f'{event.system}: {event.summary}')
        else:   # notice
            log.info(f'{event.system}: {event.summary}')
