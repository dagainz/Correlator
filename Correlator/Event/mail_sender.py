
import mako.runtime
import os
import smtplib
from mako.template import Template
from email import message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Correlator.Event.core import EventListener, Event, EventSeverity
from Correlator.config_store import ConfigType, RuntimeConfig
from Correlator.util import template_dir, Instance, SimpleException

mako.runtime.UNDEFINED = ''

EmailConfig = [{
        'smtp_server': {
            'default': 'giganode1',
            'desc': 'SMTP Server',
            'type': ConfigType.STRING
        },
        'from': {
            'default': 'admin@nowhere.com',
            'desc': 'Value of the Email From: Field',
            'type': ConfigType.EMAIL
        },
        'to': {
            'default': 'nobody',
            'desc': 'Value of the Email To: Field',
            'type': ConfigType.EMAIL
        },
        'html': {
            'default': True,
            'desc': 'Send HTML formatted email',
            'type': ConfigType.BOOLEAN
        },
        'template': {
            'default': 'mail_sender',
            'desc': 'Email template filename prefix',
            'type': ConfigType.STRING
        }
}]


class Email(EventListener):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.add_to_config(EmailConfig)

        self.template_dir = template_dir()
        self.html_email = None
        self.smtp_server = None
        self.email_from = None
        self.email_to = None

        self.template_name = None

    def initialize(self):
        self.log.debug('Initialize')

        bad_params = []
        self.html_email = self.get_config('html')
        if not self.html_email:
            bad_params.append('html')

        self.smtp_server = self.get_config('smtp_server')
        if not self.smtp_server:
            bad_params.append('smtp_server')

        self.email_from = self.get_config('from')
        if not self.email_from:
            bad_params.append('from')

        self.email_to = self.get_config('to')
        if not self.email_to:
            bad_params.append('to')

        self.template_name = self.get_config('template')
        if not self.email_to:
            bad_params.append('template')

        if bad_params:
            raise SimpleException('Invalid or missing configuration '
                                  'parameter(s): ' + ', '.join(bad_params))

    def process_event(self, event: Event):

        html_type = 'text/html'
        args = {}

        # Check for HTML

        html_template = self.template_name + '-html.mako'
        text_template = self.template_name + '-text.mako'

        self.log.debug(f'self.html_email: {self.html_email}')

        if (self.html_email
            and html_type in event.content_types
            and os.path.isfile(os.path.join(self.template_dir, html_template))):

            template_name = html_template
            content_type = html_type
        else:
            if not os.path.isfile(os.path.join(self.template_dir, text_template)):
                raise ValueError(f'Can\'t open template {text_template}')
            template_name = text_template
            content_type = 'text/plain'

        template_path = os.path.join(self.template_dir, template_name)

        # Initial subject

        subject = event.summary

        data = {
            'To': self.email_to,
            'From': self.email_from,
            'Subject': subject,
            'version': Instance.Version,
            'summary': event.render_summary(content_type),
            'data_table': event.render_datatable(content_type, **args),
            'event': event
            }

        with open(template_path, "r") as t:
            contents = t.read()

            try:
                subject = Template(contents).get_def('subject').render(**data).strip()
                self.log.debug(f'subject: {subject}')
            except AttributeError:
                # No subject def
                self.log.debug('Using default subject as there is subject def in template')
            except Exception as e:
                self.log.error(f'Using default subject as there was an exception while rendering subject from email template: {e}')
                self.log.exception(e)

            # Replace with new subject, if there is one
            data['Subject'] = subject

            # Generate an email body
            message_text = Template(contents).render(**data)

            # If it appears to be correctly MIME encoded, pass it through

            if message_text[17] == 'MIME-Version: 1.0':
                self.log.debug('Passing MIME message through')
            else:
                self.log.debug('Building MIME message')
                msg = message.Message()
                msg.add_header('Content-Type', content_type)
                msg.set_payload(message_text)

        self.log.info(f'Sending email to {self.email_to}')

        smtp = smtplib.SMTP(self.smtp_server)
        smtp.sendmail(self.email_from, self.email_to, message_text)
        self.log.debug('Email sent')
