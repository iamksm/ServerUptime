import json

import pika

from server_uptime.config.settings import settings


class Beacon:
    """
    The Beacon class is responsible for sending ping messages to a RabbitMQ server.
    It establishes a connection to the RabbitMQ server and sends messages
    to a specified queue.

    Attributes:
        rabbit_user (str): The username for RabbitMQ authentication.
        rabbit_password (str): The password for RabbitMQ authentication.
        rabbit_host_ip (str): The IP address of the RabbitMQ host.
        rabbit_port (int): The port number on which RabbitMQ is running.
        rabbit_vhost (str): The virtual host for RabbitMQ.
        connection_timeout (int): The duration (in seconds) after which
            an idle connection will be destroyed.
        tz (str): The timezone to be used.
    """

    def __init__(self, queue_name: str, server_name=None):
        self.rabbit_user = settings.RABBIT_USER
        self.rabbit_password = settings.RABBIT_PASSWORD
        self.rabbit_host_ip = settings.RABBIT_HOST_IP
        self.rabbit_port = settings.RABBIT_PORT
        self.rabbit_vhost = settings.RABBIT_VHOST
        self.connection_timeout = settings.RABBIT_CONNECTION_TIMEOUT
        self.tz = settings.TIMEZONE

        self.queue_name = queue_name
        self.server_name = server_name or queue_name

        # The first thing we need to do is to establish a connection
        # with RabbitMQ server.
        # if no activity in the connection within six hours,
        # destroy/block the connection to save resources
        self.create_connection_to_rabbitmq_host()

    def create_connection_to_rabbitmq_host(self):
        """
        Establishes a connection to the RabbitMQ host using the provided credentials.
        """
        self.timeout = f"blocked_connection_timeout={self.connection_timeout}"
        rabbit_url = f"amqp://{self.rabbit_user}:{self.rabbit_password}@{self.rabbit_host_ip}:{self.rabbit_port}/{self.rabbit_vhost}?{self.timeout}"  # noqa

        self.connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(
            exchange="SERVER-UPTIME", exchange_type="direct", durable=True
        )

        # Next, before sending we need to make sure the recipient queue exists.
        # If we send a message to non-existing location,
        # RabbitMQ will just drop the message.
        # Let's create a queue to which the message will be delivered:
        self.channel.queue_declare(
            queue=self.queue_name,
            # we need to make sure that the queue will survive a RabbitMQ node restart.
            # In order to do so, we need to declare it as durable:
            durable=True,
        )

        # Bind the created queue to the created Exchange
        self.channel.queue_bind(
            queue=self.queue_name,
            exchange="SERVER-UPTIME",
            routing_key=self.queue_name,
        )

    def send_ping(self):
        """
        Sends a ping message to the specified queue in RabbitMQ.

        The message contains a count of 1 and the name of the server (optional).
        The count represents the number of seconds the server has been up
        since the last ping.
        If no server name is provided, the queue_name will be used as the server name.
        """
        if self.connection.is_closed or self.channel.is_closed:
            self.create_connection_to_rabbitmq_host()

        # This is a primitive uptime system that basically sends 1 and the server name.
        # The watch_tower will then consume the count and update the uptime in the DB
        # The 1s are basically the seconds the server has been up, if none is sent then
        # that's how long the server is down.
        # Add them up for a particular day and you get the duration to which the server
        # has been up in seconds :)
        msg = {"count": 1, "server_name": self.server_name.upper()}
        body = json.dumps(msg)

        self.channel.basic_publish(
            exchange="SERVER-UPTIME",
            routing_key=self.queue_name,
            body=body.encode("utf-8"),
            mandatory=True,
            properties=pika.BasicProperties(
                delivery_mode=pika.spec.PERSISTENT_DELIVERY_MODE
            ),
        )
        print(f" [x] Sent {msg}")
