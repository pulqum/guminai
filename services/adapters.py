from db import save_chat_history
from services.core_interfaces import ContextProvider, LLMClient, ChatHistorySaver
from utils.context import generate_context, generate_context2


class VectorStoreContextProvider(ContextProvider):
    def __init__(self, vector_store_manager):
        self.vector_store_manager = vector_store_manager

    def generate_chat_context(self, question):
        return generate_context(question, self.vector_store_manager)

    def generate_map_context(self, question):
        return generate_context2(question, self.vector_store_manager)


class CompletionExecutorClient(LLMClient):
    def __init__(self, completion_executor):
        self.completion_executor = completion_executor

    def generate(self, request_data):
        return self.completion_executor.execute(request_data)


class SqliteChatHistorySaver(ChatHistorySaver):
    def save(self, user_message, bot_response):
        save_chat_history(user_message, bot_response)
