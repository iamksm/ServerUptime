from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Tuple
from urllib.parse import quote_plus

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    pool,
)
from sqlalchemy.orm import declarative_base, relationship

from server_uptime.app.utils import localize_datetime
from server_uptime.config.settings import settings

Base = declarative_base()


class Server(Base):
    __tablename__ = "server"

    id = Column(Integer, primary_key=True)
    name = Column(String(30))
    created = Column(DateTime)
    total_uptime = relationship(
        "Uptime", back_populates="server", cascade="all, delete-orphan"
    )


class Uptime(Base):
    __tablename__ = "uptime"

    id = Column(Integer, primary_key=True)
    record_date = Column(Date)
    last_updated = Column(DateTime)  # Last received update
    uptime = Column(Integer)
    uptime_percentage = Column(Float)  # Current uptime percentage
    server_id = Column(ForeignKey("server.id"))
    server = relationship("Server", back_populates="total_uptime")


class DBOps:
    """
    The DBOps class provides functionality to interact with a PostgreSQL
    database using SQLAlchemy.
    It manages database connections, table operations, and CRUD operations
    for server and uptime data.

    Attributes:
        USER (str): The username for the PostgreSQL database connection.
        PASS (str): The password for the PostgreSQL database connection.
        HOST (str): The IP address or hostname of the PostgreSQL server.
        DB (str): The name of the PostgreSQL database.
        PORT (int): The port number on which the PostgreSQL server is running.
    """

    def __init__(self) -> None:
        self.USER = settings.DB_USERNAME
        self.PASS = settings.DB_PASSWORD
        self.HOST = settings.DB_IP
        self.DB = settings.DB_NAME
        self.PORT = settings.DB_PORT
        self.tz = settings.TIMEZONE

        self.create_tables()  # This is idempotent

    def get_conn_string(self):
        """Returns the connection string for the PostgreSQL database."""
        user = quote_plus(self.USER)
        password = quote_plus(self.PASS)
        conn_string = (
            f"postgresql+psycopg2://{user}:{password}@{self.HOST}:{self.PORT}/{self.DB}"
        )
        return conn_string

    def get_engine_and_metadata(
        self, conn_string, pool_recycle=3600, poolclass=pool.QueuePool
    ):
        """Sets up the SQLAlchemy engine and binds metadata for the database."""
        engine = create_engine(
            conn_string, pool_recycle=pool_recycle, poolclass=poolclass
        )
        metadata = MetaData(engine)
        return engine, metadata

    def reflect_table(self, table):
        """Reflects a table object from the database metadata and returns it."""
        conn_string = self.get_conn_string()
        engine, meta = self.get_engine_and_metadata(conn_string)
        return Table(table, meta, autoload=True, autoload_with=engine)

    @contextmanager
    def create_connection(self, stream_results=True):
        """
        A context manager that yields a connection and bound metadata for the database.
        """
        conn_string = self.get_conn_string()
        engine, _ = self.get_engine_and_metadata(conn_string)
        connection = engine.connect().execution_options(stream_results=stream_results)
        try:
            yield connection
        finally:
            # close connection and send it to the connection pool
            connection.close()

    def create_tables(self, tables: List[Table] = list()):
        """Creates tables in the database using SQLAlchemy's metadata."""
        tables = tables or None
        conn_string = self.get_conn_string()
        engine, _ = self.get_engine_and_metadata(conn_string)
        return Base.metadata.create_all(engine, tables=tables)

    def drop_tables(self, tables: List[Table] = list()):
        """Drops tables from the database using SQLAlchemy's metadata."""
        tables = tables or None
        conn_string = self.get_conn_string()
        engine, _ = self.get_engine_and_metadata(conn_string)
        return Base.metadata.drop_all(engine, tables=tables)

    def create(self, table_name: str, **kwargs):
        """Inserts data into the specified table in the database."""
        table = self.reflect_table(table_name)
        with self.create_connection(stream_results=False) as conn:
            query = table.insert().values(**kwargs)
            conn.execute(query)

    def fetch_servers(self):
        """
        Fetches all server records from the 'server' table
        """
        table = self.reflect_table("server")
        with self.create_connection() as conn:
            query = table.select()
            results = conn.execute(query).fetchall()
            for result in results:
                yield dict(result)

    def get_server(self, name=None, id=None) -> Dict:
        """
        Retrieves a server record from the 'server' table
        based on its name or ID.
        """
        table = self.reflect_table("server")
        with self.create_connection() as conn:
            if id and not name:
                query = table.select().where(table.c.id == id)
            elif not id and name:
                query = table.select().where(table.c.name == name)
            elif id and name:
                query = table.select().where(table.c.id == id, table.c.name == name)
            else:
                raise DBOpsException("id or server name not provided")

            result = conn.execute(query).first()
            if result:
                return dict(result)
            return {}

    def get_uptime(self, date, server_id) -> Dict:
        """
        Retrieves an uptime record from the 'uptime' table
        based on the date and server ID.
        """
        table = self.reflect_table("uptime")
        with self.create_connection() as conn:
            query = table.select().where(
                table.c.record_date == date, table.c.server_id == server_id
            )
            results = conn.execute(query).first()
            if results:
                return dict(results)
            return {}

    def get_or_create_server(self, name, id=None, created=None) -> Tuple[Dict, bool]:
        """
        Retrieves a server record from the 'server' table based on
        its name or id. If the record does not exist,
        it creates a new server record.
        """
        result = self.get_server(name=name, id=id)
        if result:
            return result, False
        else:
            self.create("server", name=name, created=created)
            result = self.get_server(name=name)
            return result, True

    def update_uptime(
        self, server: dict, date: datetime.date, uptime: int, now: datetime.now
    ):
        """
        Updates the uptime record for a server in the 'uptime' table.
        """
        today_midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        parsed_creation_date = localize_datetime(server["created"], self.tz)
        start_time = max(today_midnight, parsed_creation_date)
        total_number_of_seconds_passed = (now - start_time).seconds
        percentage = (uptime / total_number_of_seconds_passed) * 100
        with self.create_connection(False) as conn:
            uptime_table = self.reflect_table("uptime")
            query = (
                uptime_table.update()
                .where(
                    uptime_table.c.server_id == server["id"],
                    uptime_table.c.record_date == date,
                )
                .values(
                    uptime=uptime,
                    last_updated=now,
                    uptime_percentage=min(round(percentage, 2), 100),
                )
            )
            conn.execute(query)


class DBOpsException(Exception):
    """A custom exception class for the DBOps class"""

    ...
