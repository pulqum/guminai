from services.adapters import SqliteChatHistorySaver


class ChatService:
    """
    최소 침습 방식으로 채팅 비즈니스 로직을 라우트에서 분리한 서비스 클래스.
    """

    def __init__(
        self,
        context_provider,
        llm_client,
        conversation_store,
        max_memory_length,
        chat_history_saver=None,
    ):
        self.context_provider = context_provider
        self.llm_client = llm_client
        self.conversation_store = conversation_store
        self.max_memory_length = max_memory_length
        self.chat_history_saver = chat_history_saver or SqliteChatHistorySaver()

    def construct_messages(self, model_preset, conversation_history, context):
        preset_text = model_preset.get('preset_text', []).copy()
        messages = preset_text + conversation_history

        if context:
            messages.append({'role': 'system', 'content': f'사전 정보: {context}'})

        return messages

    def get_model_response(self, model_preset, messages):
        request_data = model_preset.get('request_data', {}).copy()
        request_data['messages'] = messages
        return self.llm_client.generate(request_data)

    def handle_chat(self, question, model_preset):
        context = self.context_provider.generate_chat_context(question)
        conversation_history = self.conversation_store.get_history()
        conversation_history.append({'role': 'user', 'content': question})
        reset_required = len(conversation_history) > self.max_memory_length
        self.conversation_store.set_history(conversation_history)

        messages = self.construct_messages(model_preset, conversation_history, context)
        response = self.get_model_response(model_preset, messages)

        conversation_history.append({'role': 'assistant', 'content': response})
        self.conversation_store.set_history(conversation_history)
        self.chat_history_saver.save(question, response)

        reset_message = None
        if reset_required:
            self.conversation_store.clear_history()
            reset_message = '기억력이 초기화되었습니다!'

        return {'answer': response, 'reset_message': reset_message}

    def get_map_context(self, question):
        return self.context_provider.generate_map_context(question)

    def reset_conversation(self):
        self.conversation_store.clear_history()
