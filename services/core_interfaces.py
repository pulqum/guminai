from abc import ABC, abstractmethod


class ContextProvider(ABC):
    @abstractmethod
    def generate_chat_context(self, question):
        pass

    @abstractmethod
    def generate_map_context(self, question):
        pass


class LLMClient(ABC):
    @abstractmethod
    def generate(self, request_data):
        pass


class ConversationStore(ABC):
    @abstractmethod
    def get_history(self):
        pass

    @abstractmethod
    def set_history(self, history):
        pass

    @abstractmethod
    def clear_history(self):
        pass


class ChatHistorySaver(ABC):
    @abstractmethod
    def save(self, user_message, bot_response):
        pass


class CommunityPostRepository(ABC):
    @abstractmethod
    def save(self, board, author_name, title, content, source_topic=None):
        pass

    @abstractmethod
    def get_recent(self, limit=30, board=None):
        pass
