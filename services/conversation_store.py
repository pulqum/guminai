from flask import session
from services.core_interfaces import ConversationStore


class FlaskSessionConversationStore(ConversationStore):
    """
    Flask session 기반 대화 이력을 관리하는 저장소 어댑터.
    """

    def __init__(self, key='conversation_history'):
        self.key = key

    def get_history(self):
        return session.get(self.key, [])

    def set_history(self, history):
        session[self.key] = history

    def clear_history(self):
        session.pop(self.key, None)
