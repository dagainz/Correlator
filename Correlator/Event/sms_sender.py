from twilio.rest import Client

from Correlator.Event.core import EventListener, Event
from Correlator.config_store import ConfigType
from Correlator.core import SimpleException, CredentialsReq

SMSConfig = [
    {
        'from': {
            'default': '',
            'desc': 'Phone number message will be from',
            'type': ConfigType.STRING
        },

        'to': {
            'default': '',
            'desc': 'Phone number to deliver the message to',
            'type': ConfigType.STRING
        },

        'sid': {
            'default': '',
            'desc': 'Twilio account SID',
            'type': ConfigType.STRING
        }
    }
]


class SMS(EventListener):

    # GlobalConfig.add(SMSConfig)

    handler_name = 'SMS'

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.add_to_config(SMSConfig)

        self.account_sid = None
        self.auth_token = None
        self.Client = None
        self.twilio_from = None
        self.twilio_to = None

    def initialize(self):

        self.log.debug('Initializing twilio SMS module')
        # Load and validate configuration parameters

        bad_params = []

        self.twilio_from = self.get_config('from')
        if not self.twilio_from:
            bad_params.append('from')

        self.twilio_to = self.get_config('to')
        if not self.twilio_to:
            bad_params.append('to')

        self.account_sid = self.get_config('sid')
        if not self.account_sid:
            bad_params.append('sid')

        if bad_params:
            raise SimpleException('Invalid or missing configuration '
                                  'parameter(s): ' + ', '.join(bad_params))

        # Load credentials, or signify that they are missing from the keyring

        self.auth_token = self.get_creds(self.account_sid)
        if self.auth_token is None:
            raise CredentialsReq([self.account_sid])

        # Initialize twilio client object
        self.Client = Client(self.account_sid, self.auth_token)

    def process_event(self, event: Event):

        message = f'On {event.timestamp} the event {event.id} occurred. The message is: {event.summary}'

        self.Client.messages.create(
            from_=self.twilio_from,
            body=message,
            to=self.twilio_to)
        self.log.info('SMS Sent')
