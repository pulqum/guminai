"""
Agent 저장소 구현 - 데이터베이스 어댑터
"""
import logging
from uuid import uuid4
from .core_interfaces import AgentRepository


class SqliteAgentRepository(AgentRepository):
    """SQLite 기반 Agent 저장소"""

    def __init__(self, db_module):
        """
        Args:
            db_module: db.py 모듈 (save_agent, get_agent 등 함수 제공)
        """
        self.db = db_module

    def save_agent(self, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id=None, created_from="manual"):
        """
        새 에이전트를 저장하고 ID를 반환합니다.
        """
        agent_id = f"agent_{batch_id}_{uuid4().hex[:8]}" if batch_id else f"agent_{uuid4().hex[:12]}"
        result = self.db.save_agent(agent_id, nickname, region_code, citizen_type, sumin_job, persona_json, batch_id, created_from)
        return agent_id if result else None

    def get_agent(self, agent_id):
        """
        에이전트를 조회합니다.
        """
        agent = self.db.get_agent(agent_id)
        if agent:
            # persona_json이 문자열이면 JSON으로 파싱하지 않음 (필요 시 서비스에서 처리)
            return {
                "id": agent["id"],
                "nickname": agent["nickname"],
                "region_code": agent["region_code"],
                "citizen_type": agent["citizen_type"],
                "sumin_job": agent["sumin_job"],
                "influence": agent["influence"],
                "activity_freq": agent["activity_freq"],
                "persona_json": agent["persona_json"],
                "batch_id": agent["batch_id"],
                "created_from": agent["created_from"],
                "created_at": agent["created_at"],
            }
        return None

    def get_agents_by_batch(self, batch_id):
        """
        배치 ID로 여러 에이전트를 조회합니다.
        """
        agents = self.db.get_agents_by_batch(batch_id)
        return [
            {
                "id": agent["id"],
                "nickname": agent["nickname"],
                "region_code": agent["region_code"],
                "citizen_type": agent["citizen_type"],
                "sumin_job": agent["sumin_job"],
                "influence": agent["influence"],
                "persona_json": agent["persona_json"],
                "batch_id": agent["batch_id"],
            }
            for agent in agents
        ]

    def get_all_agents(self, status=1, limit=100):
        """
        활성 에이전트를 모두 조회합니다.
        """
        agents = self.db.get_all_agents(status=status)
        return [
            {
                "id": agent["id"],
                "nickname": agent["nickname"],
                "region_code": agent["region_code"],
                "sumin_job": agent["sumin_job"],
                "influence": agent["influence"],
            }
            for agent in agents[:limit]
        ]

    def delete_agents_by_batch(self, batch_id):
        """
        배치의 모든 에이전트를 삭제합니다.
        """
        return self.db.delete_agents_by_batch(batch_id)

    def save_agent_relation(self, source_id, target_id, relation_type, affinity_score, reason=None):
        """
        에이전트 간 관계를 저장합니다.
        """
        return self.db.save_agent_relation(source_id, target_id, relation_type, affinity_score, reason)

    def get_agent_relation(self, source_id, target_id):
        """
        에이전트 간 관계를 조회합니다.
        """
        return self.db.get_agent_relation(source_id, target_id)
