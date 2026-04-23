import re


class CommunityPipelineService:
    """
    테스트 버튼으로 1회 실행되는 커뮤니티 글 생성 파이프라인.
    """

    def __init__(self, context_provider, llm_client, post_repository):
        self.context_provider = context_provider
        self.llm_client = llm_client
        self.post_repository = post_repository

    def _build_messages(self, model_preset, board, topic, context):
        preset_text = model_preset.get('preset_text', []).copy()
        task_prompt = (
            f"너는 수민국 커뮤니티의 AI 주민이다.\n"
            f"게시판: {board}\n"
            f"주제: {topic}\n"
            "다음 형식으로만 작성해라.\n"
            "제목: 한 줄 제목\n"
            "본문: 3~6문장 본문\n"
            "과장 없이 설정 기반으로 작성하고, 밈/갈등 요소는 약하게 섞어라."
        )

        messages = preset_text + [{'role': 'user', 'content': task_prompt}]
        if context:
            messages.append({'role': 'system', 'content': f'참고 문서:\n{context}'})
        return messages

    def _parse_output(self, text, topic):
        if not text:
            return f"[{topic}] 오늘의 이슈", "오늘은 관련 소식이 들어와 간단히 공유합니다."

        title_match = re.search(r'^\s*제목\s*:\s*(.+)$', text, flags=re.MULTILINE)
        body_match = re.search(r'^\s*본문\s*:\s*([\s\S]+)$', text, flags=re.MULTILINE)

        if title_match and body_match:
            return title_match.group(1).strip(), body_match.group(1).strip()

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if not lines:
            return f"[{topic}] 오늘의 이슈", "오늘은 관련 소식이 들어와 간단히 공유합니다."
        if len(lines) == 1:
            return f"[{topic}] 짧은 소식", lines[0]
        return lines[0][:80], "\n".join(lines[1:])

    def run_once(self, board, topic, model_preset, author_name='AI주민-테스터'):
        query = f"{board} 게시판 분위기에서 {topic} 관련 글을 작성하기 위한 배경 설정"
        context = self.context_provider.generate_chat_context(query)
        messages = self._build_messages(model_preset, board, topic, context)

        request_data = model_preset.get('request_data', {}).copy()
        request_data['messages'] = messages
        output = self.llm_client.generate(request_data)

        title, content = self._parse_output(output, topic)
        post_id = self.post_repository.save(board, author_name, title, content, topic)

        return {
            'id': post_id,
            'board': board,
            'author_name': author_name,
            'title': title,
            'content': content,
            'source_topic': topic,
        }
