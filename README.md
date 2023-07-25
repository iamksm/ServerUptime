# ServerUptime

The ServerUptime project consists of three main files: `beacon.py`, `watch_tower.py`, and `database_adapter.py`. The `run.py` file provides two functions: `beacon` and `watch_tower`, which are used to run the project based on the environment. The project is designed to monitor server uptimes using RabbitMQ and store the data in a PostgreSQL database.

## Requirements

- Python 3.7+
- RabbitMQ server
- PostgreSQL database

## Project Setup

1. Clone this repository to your local machine:

   ```
   git clone <repository_url>
   cd <repository_directory>
   ```

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

## Configuration

Before running the project, make sure to configure the settings in the `server_uptime/config/settings_file.py` file. Update the RabbitMQ and PostgreSQL connection settings according to your environment.

## Usage

### Prerequisite
1. Setup Postgres in your Watch Tower Server
   - Use steps provided in the Packages and Installers from [Postgres](https://www.postgresql.org/download/)
   - [Setup the Database](https://www.postgresql.org/docs/current/sql-createdatabase.html) or use the default postgres db
      ```sql
      CREATE DATABASE <name>
      ```
   - [Setup a user and password](https://www.postgresql.org/docs/8.0/sql-createuser.html) to use when accessing the DB or use postgres if you prefer the default db

2. Setup RabbitMQ server
   - Use steps installation guides from [RabbitMQ](https://www.rabbitmq.com/download.html)
   - [Setup a vhost](https://www.rabbitmq.com/vhosts.html#creating)

      ```sh
      rabbitmqctl add_vhost <vhost_name>
      ```
   - [Setup a user](https://www.rabbitmq.com/rabbitmqctl.8.html#User_Management)

      ```sh
      rabbitmqctl add_user <username> <password>
      rabbitmqctl set_permissions -p <vhost> <username> ".*" ".*" ".*"
      ```


### Server(s) you want to monitor

1. Install the package in the server(s) you want to monitor

```
pip install ServerUptime
```

2. Run the program from the servers to be monitored first to start sending uptime pings

```
start_beacon -q <queue_name> -s <server_name>
```

- `<queue_name>`: The name of the RabbitMQ queue to which the ping messages will be sent.
- `<server_name>`: The name of the server being monitored (optional). If not provided, the `queue_name` will be used as the server name.

The `beacon` function will continuously send ping messages to the specified RabbitMQ queue every 1 second.

### Monitoring Server/ Main Server
1. Install the package

```
pip install ServerUptime
```

2. Run the program from the monitoring server to start consuming the messages

```
start_watch_tower -q <queue_name>
```

- `<queue_name>`: The name of the RabbitMQ queue to which the ping messages will be sent.

The `watch_tower` function will start listening for messages from the specified RabbitMQ queue and update the server uptime in the PostgreSQL database accordingly.

### Note

- It is preferred to set up and run the `beacon` functions first before starting the `watch_tower`. This ensures that the server uptimes are being sent to the RabbitMQ queue before the WatchTower consumes and updates them.

## License

This project is licensed under the [MIT License](LICENSE).
