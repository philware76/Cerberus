import logging
import socket
from typing import Dict, List

from Cerberus.deviceTypes import DEVICE_TYPES


class EthDiscovery():
    """Ethernet Discovery - listens for NESIE devices"""

    KEYS = ('IP Address', 'Name', 'Mac Address', 'Type', 'ID', 'Group')

    def search(self) -> List[Dict[str, str]]:
        """Search and return discovered devices"""
        results: List[Dict[str, str]] = []
        HOST = "0.0.0.0"
        PORT = 30303

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 5)
                sock.settimeout(3)

                sock.bind((HOST, PORT))
                logging.debug(f'Broadcasting on 255.255.255.255, port {PORT} to find NESIE devices.')

                sock.sendto(b'Discovery: Python', ('255.255.255.255', PORT))

                while True:
                    data, address = sock.recvfrom(1024)
                    values = data.decode('utf8').split()

                    if len(values) >= 3 and values != ['Discovery:', 'Python']:  # this should catch CM/MCM/ACM/S/T/U-NESIEs
                        found = DEVICE_TYPES.get(values[2], None)

                        if found is not None:
                            values.insert(2, found)
                            values.insert(0, address[0])
                            device = dict(zip(EthDiscovery.KEYS, values))
                            device['Mac Address'] = ':'.join(device['Mac Address'].lower().split('-'))
                            results.append(device)

        except socket.timeout as e:
            pass

        return results
