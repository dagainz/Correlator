import logging
import smtplib
import os
import mako.runtime
from mako.template import Template
from email import message
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from Correlator.Event.core import EventListener, Event, EventStatus
from Correlator.config import GlobalConfig, ConfigType
from Correlator.util import template_dir, Instance

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

    # GlobalConfig.add(EmailConfig)

    def __init__(self, name):

        super().__init__(name)

        self.template_dir = template_dir()
        self.html_email = None
        self.smtp_server = None
        self.email_from = None
        self.email_to = None

    def initialize(self):
        self.log.debug('Initialize')

        self.html_email = self.get_config('email.html')
        self.smtp_server = self.get_config('email.smtp_server')
        self.email_from = self.get_config('email.from')
        self.email_to = self.get_config('email.to')

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
