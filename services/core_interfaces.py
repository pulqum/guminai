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


class AgentRepository(ABC):
    """에이전트 저장소 인터페이스"""

    @abstractmethod
    def save_agent(self, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id=None, created_from="manual"):
        """에이전트를 저장하고 ID를 반환합니다"""
        pass

    @abstractmethod
    def get_agent(self, agent_id):
        """특정 에이전트를 조회합니다"""
        pass

    @abstractmethod
    def get_agents_by_batch(self, batch_id):
        """배치 ID로 에이전트들을 조회합니다"""
        pass

    @abstractmethod
    def get_all_agents(self, status=1, limit=100):
        """활성 에이전트들을 조회합니다"""
        pass

    @abstractmethod
    def delete_agents_by_batch(self, batch_id):
        """배치의 모든 에이전트를 삭제합니다"""
        pass

    @abstractmethod
    def save_agent_relation(self, source_id, target_id, relation_type, affinity_score, reason=None):
        """에이전트 간 관계를 저장합니다"""
        pass

    @abstractmethod
    def get_agent_relation(self, source_id, target_id):
        """에이전트 간 관계를 조회합니다"""
        pass
