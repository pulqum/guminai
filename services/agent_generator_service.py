"""
Agent 생성 서비스 - LLM 기반 페르소나 생성
"""
import json
import logging
import uuid
from datetime import datetime
from typing import List, Optional


logger = logging.getLogger(__name__)


class AgentGeneratorService:
    """에이전트 배치 생성 및 LLM 기반 페르소나 생성 담당"""

    def __init__(self, agent_repository, llm_client, context_provider=None):
        """
        Args:
            agent_repository: 에이전트 저장소 (CRUD 담당)
            llm_client: LLM 클라이언트 (페르소나 생성용)
            context_provider: 컨텍스트 제공자 (선택사항)
        """
        self.agent_repository = agent_repository
        self.llm_client = llm_client
        self.context_provider = context_provider

    def generate_batch(
        self,
        batch_name: str,
        count: int,
        region_code: int,
        citizen_types: List[int],
        sumin_jobs: List[str],
        context_topic: str = "수민넷 커뮤니티",
    ) -> dict:
        """
        에이전트 배치를 생성합니다.

        Args:
            batch_name: 배치 이름
            count: 생성할 에이전트 수
            region_code: 지역 코드
            citizen_types: 시민 유형 리스트
            sumin_jobs: 수민 직업 리스트
            context_topic: 페르소나 생성 배경 주제

        Returns:
            배치 생성 결과
        """
        batch_id = f"batch_{batch_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        created_agents = []
        failed = []

        for i in range(count):
            try:
                citizen_type = citizen_types[i % len(citizen_types)]
                sumin_job = sumin_jobs[i % len(sumin_jobs)]

                nickname, persona_json = self._generate_persona_with_llm(
                    i + 1, citizen_type, sumin_job
                )

                agent_id = self.agent_repository.save_agent(
                    nickname=nickname,
                    region_code=region_code,
                    citizen_type=citizen_type,
                    sumin_job=sumin_job,
                    persona_json=persona_json,
                    batch_id=batch_id,
                    created_from="generator",
                )

                if agent_id:
                    created_agents.append({"id": agent_id, "nickname": nickname})
                    logger.info(f"✓ 에이전트 생성: {nickname}")
                else:
                    failed.append(f"Agent {i+1}: 저장 실패")

            except Exception as e:
                failed.append(f"Agent {i+1}: {str(e)}")
                logger.error(f"✗ 에이전트 생성 오류: {e}")

        return {
            "batch_id": batch_id,
            "total_requested": count,
            "created_count": len(created_agents),
            "failed_count": len(failed),
            "created_agents": created_agents,
            "failed": failed,
            "status": "success" if len(created_agents) == count else "partial",
        }

    def _generate_persona_with_llm(self, index: int, citizen_type: int, sumin_job: str) -> tuple:
        """
        LLM으로 페르소나를 생성합니다.

        Returns:
            (nickname, persona_json_string)
        """
        citizen_type_map = {
            0: "무관심층",
            1: "일반시민",
            2: "관심층",
            3: "활동가",
            4: "전문가",
        }
        citizen_label = citizen_type_map.get(citizen_type, "일반시민")
        job_label = sumin_job or "직장인"

        prompt = f"""[지시사항]
수민넷 커뮤니티의 AI 주민 에이전트 페르소나를 단 1개 생성하세요. 실제 설득력 있는 사람처럼 보이도록.

[조건]
- 직업: {job_label}
- 시민 유형: {citizen_label}
- 단순 단박이 느껴지지 않도록 (특정한 개인차, 경험, 의견이 있어야 함)
- 한국어 이름과 자연스러운 자기소개

[출력 형식 - JSON만 (설명 없음)]
{{
  "name": "이름",
  "bio": "자기소개 2~3문장",
  "interests": ["관심사1", "관심사2", "관심사3"],
  "personality": "성격 키워드",
  "influence": 0~100,
  "activity_freq": 0.0~1.0
}}

JSON만 출력. 마크다운 코드블록이나 추가 텍스트 없음."""

        try:
            response = self.llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                model_preset="default",
                max_tokens=400,
            )

            if "{" in response and "}" in response:
                json_start = response.find("{")
                json_end = response.rfind("}") + 1
                json_str = response[json_start:json_end]
                persona_dict = json.loads(json_str)

                nickname = persona_dict.get("name", f"{sumin_job}_{index}")
                logger.info(f"✓ AI 페르소나: {nickname}")

                return nickname, json.dumps(persona_dict, ensure_ascii=False)
            else:
                raise ValueError("JSON 추출 실패")

        except Exception as e:
            logger.warning(f"LLM 페르소나 생성 실패, 폴백 사용: {e}")
            nickname = f"{job_label}_{uuid.uuid4().hex[:4]}"
            persona_dict = {
                "name": nickname,
                "citizen_type": citizen_type,
                "job": sumin_job,
                "bio": f"{citizen_label} 중 {job_label}로서 수민넷에 적극 참여합니다.",
                "interests": ["지역 발전", "커뮤니티", "시민 소통"],
                "influence": 50,
                "activity_freq": 0.6,
                "personality": "현실적이고 성실한",
            }
            return nickname, json.dumps(persona_dict, ensure_ascii=False)

    def get_batch_info(self, batch_id: str) -> dict:
        """배치의 에이전트 목록을 조회합니다."""
        agents = self.agent_repository.get_agents_by_batch(batch_id)
        return {
            "batch_id": batch_id,
            "agent_count": len(agents),
            "agents": agents,
        }

    def delete_batch(self, batch_id: str) -> bool:
        """배치의 모든 에이전트를 삭제합니다."""
        return self.agent_repository.delete_agents_by_batch(batch_id)
