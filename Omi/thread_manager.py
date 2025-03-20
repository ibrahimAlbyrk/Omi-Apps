import threading
from abc import ABC, abstractmethod


class IThreadManager(ABC):
    @abstractmethod
    def start_thread(self, thread_id: str, target_function, args: tuple):
        raise NotImplementedError

    @abstractmethod
    def is_thread_running(self, thread_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def stop_thread(self, thread_id: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_running(self, thread_id: str) -> bool:
        raise NotImplementedError


class ThreadManager(IThreadManager):
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ThreadManager, cls).__new__(cls)
            cls._instance.threads = {}
            cls._instance.stop_flags = {}
        return cls._instance

    def is_thread_running(self, thread_id: str) -> bool:
        is_running =thread_id in self.threads and self.threads[thread_id].is_running()
        return is_running

    def start_thread(self, thread_id: str, target_function, args: tuple):
        if self.is_thread_running(thread_id):
            return False

        stop_event = threading.Event()
        self.stop_flags[thread_id] = stop_event

        def wrapper_function(*arguments):
            target_function(stop_event, *arguments)

        thread = threading.Thread(target=wrapper_function, args=args, daemon=True)
        self.threads[thread_id] = thread
        thread.start()
        return True

    def stop_thread(self, thread_id: str) -> bool:
        if thread_id in self.stop_flags:
            self.stop_flags.pop(thread_id).set()
            self.threads.pop(thread_id)
            return True
        return False

    def is_running(self, thread_id: str) -> bool:
        return self.threads.get(thread_id, None) and self.threads[thread_id].is_alive()


thread_manager = ThreadManager()
