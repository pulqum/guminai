from db import get_recent_community_posts, save_chat_history, save_community_post, get_community_post, increment_community_post_view, vote_community_post
from services.core_interfaces import ContextProvider, LLMClient, ChatHistorySaver, CommunityPostRepository
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
    
    def complete(self, messages, model_preset='default', max_tokens=1000):
        """messages 기반의 완성 생성 래퍼"""
        # 간단한 요청 데이터 구성
        request_data = {
            'messages': messages,
            'maxTokens': max_tokens
        }
        return self.completion_executor.execute(request_data)


class SqliteChatHistorySaver(ChatHistorySaver):
    def save(self, user_message, bot_response):
        save_chat_history(user_message, bot_response)


class SqliteCommunityPostRepository(CommunityPostRepository):
    def save(self, board, author_name, title, content, source_topic=None):
        return save_community_post(board, author_name, title, content, source_topic)

    def get_recent(self, limit=30, board=None, sort='latest'):
        return get_recent_community_posts(limit=limit, board=board, sort=sort)

    def get_post(self, post_id):
        return get_community_post(post_id)

    def increment_post_view(self, post_id):
        return increment_community_post_view(post_id)

    def vote_post(self, post_id, vote_type):
        return vote_community_post(post_id, vote_type)
