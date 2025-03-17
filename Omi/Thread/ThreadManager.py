import threading


class ThreadManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThreadManager, cls).__new__(cls)
            cls._instance.threads = {}  # _id → Thread
            cls._instance.thread_status = {}  # _id → Is thread working?
        return cls._instance

    def start_thread(self, _id, target_function, *args):
        if _id in self.threads and self.thread_status.get(_id, False):
            return False

        self.thread_status[_id] = True
        thread = threading.Thread(target=target_function, args=(_id, *args), daemon=True)
        self.threads[_id] = thread
        thread.start()
        return True

    def stop_thread(self, _id):
        if _id in self.threads:
            self.thread_status[_id] = False
            return True
        return False

    def is_running(self, _id):
        return self.thread_status.get(__id, False)

    def stop_all(self):
        for _id in self.threads.keys():
            self.thread_status[_id] = False

thread_manager = ThreadManager()