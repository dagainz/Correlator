from Correlator.Event.core import EventListener, Event, log


class LogbackListener(EventListener):

    def __init__(self):
        # todo: Why?
        pass

    def process_event(self, event: Event):
        if event.is_error:
            log.error(f'{event.system}: {event.summary}')
        elif event.is_warning:
            log.warning(f'{event.system}: {event.summary}')
        elif event.is_audit:
            text = event.render_text()
            if text:
                log.info(f'{event.system}: Audit({event.audit_id}):'
                         f' {text}')
            else:
                log.info(f'{event.system}: Audit({event.audit_id}): '
                         f'{event.summary}')
        else:   # notice
            log.info(f'{event.system}: {event.summary}')
