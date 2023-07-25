import json
from datetime import datetime

import pika

from server_uptime.app.database_adapter import DBOps
from server_uptime.app.utils import localize_datetime
from server_uptime.config.settings import settings


class WatchTower:
    """
    The WatchTower class is responsible for monitoring and updating server
    ptime information by consuming messages from a RabbitMQ queue.
    It listens for messages from the queue, which contain server uptime
    data, and updates the server uptime in the database.

    Attributes:
        rabbit_user (str): The username for RabbitMQ authentication.
        rabbit_password (str): The password for RabbitMQ authentication.
        rabbit_host_ip (str): The IP address of the RabbitMQ host.
        rabbit_port (int): The port number on which RabbitMQ is running.
        rabbit_vhost (str): The virtual host for RabbitMQ.
        connection_timeout (int): The duration (in seconds) after which
            an idle connection will be destroyed.
        tz (str): The timezone to be used.

    Note:
        - The callback function is executed when a message is received from the RabbitMQ
            queue.
        - The update_uptime_to_db method updates the server's uptime information in the
            database.
        - The consume method continuously listens for messages and updates the database
            until interrupted.
        - The WatchTower class requires the DBOps class from app.database_adapter and
            RabbitMQ settings from config.settings to be correctly set up.
    """

    def __init__(self, queue_name):
        self.rabbit_user = settings.RABBIT_USER
        self.rabbit_password = settings.RABBIT_PASSWORD
        self.rabbit_host_ip = settings.RABBIT_HOST_IP
        self.rabbit_port = settings.RABBIT_PORT
        self.rabbit_vhost = settings.RABBIT_VHOST
        self.connection_timeout = settings.RABBIT_CONNECTION_TIMEOUT
        self.tz = settings.TIMEZONE

        self.queue_name = queue_name

        # The first thing we need to do is to establish a connection
        # with RabbitMQ server.
        # if no activity in the connection within six hours,
        # destroy/block the connection to save resources
        self.create_connection_to_rabbitmq_host()

        self.db = DBOps()

    def create_connection_to_rabbitmq_host(self):
        """
        Establishes a connection to the RabbitMQ host using the provided credentials.
        """
        self.timeout = f"blocked_connection_timeout={self.connection_timeout}"
        rabbit_url = f"amqp://{self.rabbit_user}:{self.rabbit_password}@{self.rabbit_host_ip}:{self.rabbit_port}/{self.rabbit_vhost}?{self.timeout}"  # noqa

        # Establish a connection with RabbitMQ server.
        self.connection = pika.BlockingConnection(pika.URLParameters(rabbit_url))
        self.channel = self.connection.channel()

        self.channel.exchange_declare(
            exchange="SERVER-UPTIME",
            exchange_type="direct",
            durable=True,
            passive=True,
        )

        self.channel.queue_declare(queue=self.queue_name, durable=True, passive=True)

        # Bind a queue to the defined exchange
        self.channel.queue_bind(
            exchange="SERVER-UPTIME",
            queue=self.queue_name,
            routing_key=self.queue_name,
        )

    def callback(self, ch, method, properties, body):
        """
        The function processes received messages from the RabbitMQ queue.
        It then updates the server uptime in the database .
        """
        msg = json.loads(body)
        count = int(msg["count"])
        server_name = msg["server_name"]

        print(f" [x] RECEIVED UPTIME FROM {server_name.upper()}")
        self.update_uptime_to_db(count, server_name)
        print(f" [x] DONE UPDATING {server_name.upper()} UPTIME")

        ch.basic_ack(delivery_tag=method.delivery_tag)

    def update_uptime_to_db(self, count, server_name):
        """
        Updates the server's uptime in the database with the received count value.
        """
        now = localize_datetime(datetime.now(), self.tz)
        date = now.date()

        server, _ = self.db.get_or_create_server(name=server_name, created=now)
        current_uptime = self.db.get_uptime(server_id=server["id"], date=date)
        if current_uptime:
            uptime = int(current_uptime["uptime"]) + int(count)
            self.db.update_uptime(server, date, uptime, now)
        else:
            uptime_data = {
                "record_date": date,
                "last_updated": now,
                "uptime": int(count),
                "server_id": server["id"],
                "uptime_percentage": 100,
            }
            self.db.create("uptime", **uptime_data)

    def consume(self):
        """
        Listens for messages in the specified RabbitMQ queue and processes them
        using the callback function. It continuously listens for new messages
        until interrupted by the user or an exception occurs.
        """
        try:
            if self.connection.is_closed or self.channel.is_closed:
                self.create_connection_to_rabbitmq_host()

            # Next, we need to tell RabbitMQ that this particular callback function
            # should receive messages from our queue:
            self.channel.basic_consume(
                queue=self.queue_name, on_message_callback=self.callback
            )

            print(" [*] Waiting for messages. To exit press CTRL+C")

            self.channel.start_consuming()
        except pika.exceptions.ConnectionClosedByBroker:
            msg = """
            CONNECTION CLOSED BY THE BROKER!!!

            RE-INITIALIZING QUEUED MESSAGES CONSUMPTION
            """
            print(msg)

            self.consume(self.queue_name)
        except KeyboardInterrupt:
            self.channel.close()
            self.connection.close()
