import sqlite3
import threading
from time import sleep


class DatabaseManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, db_name="database.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False

        return cls._instance

    def __init__(self, db_name="database.db"):
        if self._initialized:
            return

        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._initialized = True

    def execute(self, query, params=None):
        if params is None:
            params = ()

        with self._lock:
            self.cursor.execute(query, params)
            self.connection.commit()

    def fetch_all(self, query, params=None):
        if params is None:
            params = ()

        with self._lock:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()

    def fetch_one(self, query, params=None):
        if params is None:
            params = ()

        with self._lock:
            self.cursor.execute(query, params)
            return self.cursor.fetchone()

    def close(self):
        self.connection.close()

    def drop_database(self):
        query = "DROP TABLE IF EXISTS users;"
        self.execute(query)


class UserRepository:
    def __init__(self, db_manager):
        self.db = db_manager
        self.create_table()

    def create_table(self):
        query = """
        CREATE TABLE IF NOT EXISTS users (
        uid INTEGER PRIMARY KEY AUTOINCREMENT,
        google_credentials TEXT NOT NULL
        );
        """

        self.db.execute(query)

    def add_user(self, uid, google_credentials=None):
        query = "INSERT INTO users (uid, google_credentials) VALUES (?, ?)"
        self.db.execute(query, (uid, google_credentials))

    def delete_user(self, uid):
        query = "DELETE FROM users WHERE uid = ?;"
        self.db.execute(query, (uid,))

    def get_credentials(self, uid):
        query = "SELECT google_credentials FROM users WHERE uid = ?;"
        return self.db.fetch_one(query, (uid,))

    def update_credentials(self, uid, new_google_credentials):
        query = "UPDATE users SET google_credentials = ? WHERE uid = ?;"
        self.db.execute(query, (new_google_credentials, uid))


db = DatabaseManager()
user_repository = UserRepository(db)


def main():
    user_repository.delete_user(123)
    user_repository.delete_user(891230897312897)


if __name__ == '__main__':
    main()
