import click

from server_uptime.run import beacon, watch_tower


@click.command()
@click.option(
    "-s",
    "--server-name",
    "server_name",
    default="TEST-UPTIME-SERVER-NAME",
    help="This should be the name used to uniquely identify your server",
)
@click.option(
    "-q",
    "--queue-name",
    "queue_name",
    default="test_uptime_queue",
    help="Name to use when setting up a queue in rabbit to hold the messages",
)
def start_beacon(queue_name, server_name):
    beacon(queue_name, server_name)


@click.command()
@click.option(
    "-q",
    "--queue-name",
    "queue_name",
    default="test_uptime_queue",
    help="Name to use when setting up a queue in rabbit to hold the messages",
)
def start_watch_tower(queue_name):
    watch_tower(queue_name)
