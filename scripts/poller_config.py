import json
from CiscoNX import switch_collector
from insite_plugin import InsitePlugin


class Plugin(InsitePlugin):

    def can_group(self):
        return False

    def fetch(self, hosts):

        try:

            self.collector

        except Exception:

            params = {
                'user': 'admin',
                'password': 'Evertz123',
                'host': hosts[-1],
                'magnum_cache': {
                    'insite': '172.16.112.20',
                    'nature': 'mag-1',
                    'cluster_ip': '172.17.143.201',
                    'core_link_prefix': "Ethernet1/",
                    #'sub_interfaces': True
                },
                'netflow': {
                    'insite': '172.16.112.20'
                }
            }

            self.collector = switch_collector(**params)

        return json.dumps(self.collector.collect)
