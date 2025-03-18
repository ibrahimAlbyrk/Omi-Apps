import sqlite3
import threading


class ISQLiteDatabaseManager:
    def execute(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def fetch_all(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def fetch_one(self, query: str, params: tuple = ()):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class IUserRepository:
    def add_user(self, uid: str, google_credentials: str = None):
        raise NotImplementedError

    def has_user(self, uid: str) -> bool:
        raise NotImplementedError

    def delete_user(self, uid: str):
        raise NotImplementedError

    def get_credentials(self, uid: str):
        raise NotImplementedError

    def update_credentials(self, uid: str, new_google_credentials: str):
        raise NotImplementedError


class SQLiteDatabaseManager(ISQLiteDatabaseManager):
    def __init__(self, db_name="database.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._lock = threading.Lock()

    def execute(self, query: str, params: tuple = ()):
        with self._lock:
            self.cursor.execute(query, params)
            self.connection.commit()

    def fetch_all(self, query: str, params: tuple = ()):
        with self._lock:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()

    def fetch_one(self, query: str, params: tuple = ()):
        with self._lock:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()

    def close(self):
        self.connection.close()


class UserRepository(IUserRepository):
    def __init__(self, db_manager: SQLiteDatabaseManager):
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
