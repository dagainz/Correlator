"""
Correlator module for: Transmission daemon

Process: completed torrents

"""

import re
from dataclasses import dataclass

from Correlator.Event.core import Event, StatsEvent
from Correlator.util import Module


class TransmissionCompleted(Event):

    schema = [
        ['server', 'Transmission Server'],
        ['torrent', 'Torrent name']
     ]
    templates = {
        'text/plain': {
            'summary': '${torrent} downloaded on server ${server}'
        },
        'text/html': {
            'summary': '<strong>${torrent}</strong> downloaded on server '
                       '<strong>${server}</strong>'
        }
    }

    # default severity


class TransmissionStats(StatsEvent):

    schema = [
        ['torrents_downloaded', 'Torrents downloaded']
    ]
    templates = {
        'text/plain': {
            'summary': 'Statistics: ${torrents_downloaded} Torrent(s) '
                       'downloaded'
        },
        'text/html': {
            'summary': 'Statistics: <strong>${torrents_downloaded}</strong> '
                       'Torrent(s) downloaded'
        },
    }


@dataclass
class TransmissionStore:

    torrents_downloaded = 0


class Transmission(Module):
    def __init__(self, module_name: str):

        super().__init__(module_name)

        self.description = 'Transmission daemon'
        self.identifier = 'transmission'
        self.model = TransmissionStore

    def initialize(self):

        self.log.debug('Process module related configuration items')

        # No configuration items for this module

    def maintenance(self):
        """ perform module maintenance """

        # This module requires no periodic maintenance

        pass

    def post_init_store(self):
        pass

    def clear_statistics(self):
        self.store.torrents_downloaded = 0

    def statistics(self, reset=False):

        data = {
            'torrents_downloaded': self.store.torrents_downloaded

        }
        self.dispatch_event(TransmissionStats(data))

        if reset:
            self.clear_statistics()

    def detect_complete(self, string):

        m = re.match(r'\[.*?\]\s+(.+?)\s+State changed from "Incomplete" to "Complete"', string)
        if m:
            torrent_name = m.group(1)
            self.log.debug(f'Torrent {torrent_name} detected as complete')
            self.store.torrents_downloaded += 1
            return torrent_name
        return None

    def process_record(self, record):

        if record.appname.lower() != 'transmission-daemon':
            return

        self.log.debug(f'Checking transmission record: {record.detail}')
        torrent_name = self.detect_complete(record.detail)
        if torrent_name:
            self.dispatch_event(
                TransmissionCompleted({
                    'torrent': torrent_name,
                    'server': record.hostname
                })
            )
            return
