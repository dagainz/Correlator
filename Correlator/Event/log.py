from Correlator.Event.core import EventListener, Event, log


class LogbackListener(EventListener):

    name = 'Logback'

    def __init__(self):
        # todo: Why?
        pass

    def process_event(self, event: Event):
        if event.is_error:
            log.error(f'{event.system}: {event.summary}')
        elif event.is_warning:
            log.warning(f'{event.system}: {event.summary}')
        elif event.is_audit:
            log.info(repr(event))
        else:   # notice
            log.info(f'{event.system}: {event.summary}')
