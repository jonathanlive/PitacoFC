# fastapi_server/thread_manager.py
import time

class ThreadManager:
    def __init__(self):
        self.user_threads = {}  # { sender: { "thread_id": str, "last_activity": timestamp, "message_count": int } }
        self.MAX_MESSAGES_PER_THREAD = 20  # Por exemplo: renova a cada 20 interações

    def get_thread(self, sender):
        data = self.user_threads.get(sender)
        if data and data["message_count"] < self.MAX_MESSAGES_PER_THREAD:
            return data["thread_id"]
        return None

    def register_thread(self, sender, thread_id):
        self.user_threads[sender] = {
            "thread_id": thread_id,
            "last_activity": time.time(),
            "message_count": 0
        }

    def increment_message_count(self, sender):
        if sender in self.user_threads:
            self.user_threads[sender]["message_count"] += 1
            self.user_threads[sender]["last_activity"] = time.time()

    def clear_thread(self, sender):
        if sender in self.user_threads:
            del self.user_threads[sender]
