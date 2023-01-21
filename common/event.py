from datetime import datetime


class Event:
    def __init__(self, summary, record, **kwargs):

        self.system = 'System'
        self.data = None
        self.record = record
        self.is_error = False
        self.is_warning = False
        self.summary = summary
        self.datetime_obj = datetime.now()
        self.timestamp = self.datetime_obj.strftime('%Y-%m-%d %H:%M:%S')
        self.system = kwargs.get('system', 'None')

    def __repr__(self):
        raise NotImplementedError


class ErrorEvent(Event):

    def __init__(self, summary, record, **kwargs):
        super().__init__(summary, record, **kwargs)
        self.is_error = True

    def __repr__(self):
        return f'ERROR: {self.timestamp}: {self.summary}'


class WarningEvent(Event):

    def __init__(self, summary, record, **kwargs):
        super().__init__(summary, record, **kwargs)
        self.is_warning = True

    def __repr__(self):
        return f'WARNING: {self.timestamp}: {self.summary}'


class NoticeEvent(Event):

    def __repr__(self):
        return f'NOTICE: {self.timestamp}: {self.summary}'


class EventListener:
    def process_event(self, event: Event):
        raise NotImplementedError


class EventProcessor:
    def __init__(self, log):
        self.log = log
        self.listeners: list[EventListener] = []

    def register_listener(self, event_listener: EventListener):
        self.listeners.append(event_listener)

    def dispatch_event(self, event: Event):
        for listener in self.listeners:
            listener.process_event(event)
        # self.log.info('Handling event {}'.format(str(event)))


class LogbackListener(EventListener):

    def __init__(self, log):
        self.log = log

    def process_event(self, event: Event):
        if event.is_error:
            self.log.error(f'{event.system}: {event.summary}')
        elif event.is_warning:
            self.log.warn(f'{event.system}: {event.summary}')
        else:
            self.log.info(f'{event.system}: {event.summary}')

