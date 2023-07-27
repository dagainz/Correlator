
import mako.runtime
import os
import smtplib
from mako.template import Template
from email import message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Correlator.Event.core import EventListener, Event, EventStatus
from Correlator.global_config import GlobalConfig, ConfigType
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

        if bad_params:
            raise SimpleException('Invalid or missing configuration '
                                  'parameter(s): ' + ', '.join(bad_params))


    def process_event(self, event: Event):

        if event.status == EventStatus.Error:
            base_def = 'error'
        elif event.status == EventStatus.Warning:
            base_def = 'warning'
        else:
            base_def = 'notice'

        template_name = 'email.mako'

        html_detail = event.render_html()
        text_detail = event.render_text()

        if text_detail is None:
            text_detail = event.summary

        html_content = None
        if event.event_desc is not None:
            summary = event.event_desc
        else:
            summary = event.summary

        # Render text message body

        template_path = os.path.join(self.template_dir, template_name)

        if not os.path.isfile(template_path):
            raise ValueError(f'Required template {template_path} missing')

        data = {
            'version': Instance.Version,
            'text_detail': text_detail,
            'html_detail': html_detail,
            'summary': summary
            }

        if html_detail and self.html_email:
            # Render HTML message body
            html_content = Template(
                filename=template_path).get_def(
                f'{base_def}_html').render(**data)

        email_template = Template(filename=template_path)
        text_content = email_template.get_def(f'{base_def}_text').render(**data)
        subject = email_template.get_def(f'{base_def}_subject').render(**data)

        if html_content:
            msg = MIMEMultipart('alternative')
            text_part = MIMEText(text_content, 'plain')
            html_part = MIMEText(html_content, 'html')
            msg.attach(text_part)
            msg.attach(html_part)
        else:
            msg = message.Message()
            msg.add_header('Content-Type', 'text')
            msg.set_payload(text_content)

        msg['From'] = self.email_from
        msg['To'] = self.email_to
        msg['Subject'] = subject

        self.log.info(f'Sending email to {self.email_to}')

        smtp = smtplib.SMTP(self.smtp_server)
        smtp.sendmail(msg['From'], msg['To'], msg.as_string())
        self.log.debug('Email sent')
