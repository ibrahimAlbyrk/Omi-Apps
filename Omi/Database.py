import sqlite3
import threading

import Logger
from Logger import LoggerType, FormatterType
from abc import ABC, abstractmethod

logger = Logger.Manager("Database",
                        FormatterType.ADVANCED,
                        LoggerType.CONSOLE)


class ISQLiteDatabaseManager:
    def execute(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def fetch_all(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def fetch_one(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class SQLiteDatabaseManager(ISQLiteDatabaseManager):
    _instance = None
    _lock = Lock()

    def __new__(cls, db_path="database.db"):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(SQLiteDatabaseManager, cls).__new__(cls)
                cls._instance._initialize(db_path)
        return cls._instance

    def _initialize(self, db_path):
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def execute(self, query: str, params: tuple = ()):
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
        except sqlite3.Error as e:
            logger.error(f"Database error: {e}")

    def fetch_all(self, query: str, params: tuple = ()):
        with self._lock:
            try:
                self.cursor.execute(query, params)
                return self.cursor.fetchall()
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}")
                return None

    def fetch_one(self, query: str, params: tuple = ()):
        with self._lock:
            try:
                self.cursor.execute(query, params)
                return self.cursor.fetchone()
            except sqlite3.Error as e:
                logger.error(f"Database error: {e}")
                return None

    def close(self):
        self.connection.close()


class IUserRepository(ABC):
    @abstractmethod
    def add_user(self, uid: str, google_credentials: str = None):
        raise NotImplementedError

    @abstractmethod
    def has_user(self, uid: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def delete_user(self, uid: str):
        raise NotImplementedError

    @abstractmethod
    def get_credentials(self, uid: str):
        raise NotImplementedError

    @abstractmethod
    def update_credentials(self, uid: str, new_google_credentials: str):
        raise NotImplementedError


class UserRepository(IUserRepository):
    def __init__(self, db_manager: ISQLiteDatabaseManager):
        self.db = db_manager
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
            uid TEXT PRIMARY KEY,
            google_credentials TEXT NOT NULL
        );
        """
        self.db.execute(query)

    def add_user(self, uid: str, google_credentials: str = None):
        query = "INSERT INTO users (uid, google_credentials) VALUES (?, ?)"
        self.db.execute(query, (uid, google_credentials))

    def has_user(self, uid: str) -> bool:
        query = "SELECT 1 FROM users WHERE uid = ?;"
        return self.db.fetch_one(query, (uid,)) is not None

    def get_all_users(self) -> []:
        query = "SELECT * FROM users;"
        results = self.db.fetch_all(query)
        return [{"uid": row["uid"], "google_credentials": row["google_credentials"]} for row in results]

    def delete_user(self, uid: str):
        query = "DELETE FROM users WHERE uid = ?;"
        self.db.execute(query, (uid,))

    def get_credentials(self, uid: str):
        query = "SELECT google_credentials FROM users WHERE uid = ?;"
        result = self.db.fetch_one(query, (uid,))
        return result["google_credentials"] if result else None

    def update_credentials(self, uid: str, new_google_credentials: str):
        query = "UPDATE users SET google_credentials = ? WHERE uid = ?;"
        self.db.execute(query, (new_google_credentials, uid))


class IMailRepository(ABC):
    @abstractmethod
    def add_processed_email(self, uid: str, email_id: str):
        raise NotImplementedError

    @abstractmethod
    def is_email_processed(self, uid: str, email_id: str) -> bool:
        raise NotImplementedError


class MailRepository(IMailRepository):
    def __init__(self, db_manager: ISQLiteDatabaseManager):
        self.db = db_manager
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS processed_emails (
            uid TEXT NOT NULL,
            email_id TEXT NOT NULL,
            PRIMARY KEY (uid, email_id)
        );
        """
        self.db.execute(query)

    def add_processed_email(self, uid: str, email_id: str):
        query = "INSERT INTO processed_emails (uid, email_id) VALUES (?, ?) ON CONFLICT(uid, email_id) DO NOTHING;"
        self.db.execute(query, (uid, email_id))

    def is_email_processed(self, uid: str, email_id: str) -> bool:
        query = "SELECT 1 FROM processed_emails WHERE uid = ? AND email_id = ?;"
        return self.db.fetch_one(query, (uid, email_id)) is not None
