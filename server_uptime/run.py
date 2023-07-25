import time

from server_uptime.app.beacon import Beacon
from server_uptime.app.watch_tower import WatchTower


def beacon(queue_name: str, server_name=None):
    beacon = Beacon(queue_name, server_name)
    while True:
        try:
            # Send ping every 1 second
            beacon.send_ping()
            time.sleep(1)
        except KeyboardInterrupt:
            beacon.connection.close()


def watch_tower(queue_name: str):
    watch_tower = WatchTower(queue_name)
    watch_tower.consume()
