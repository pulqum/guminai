document.addEventListener('DOMContentLoaded', function () {
    const runButton = document.getElementById('run-once-button');
    const generateBatchButton = document.getElementById('generate-batch-button');
    const boardSelect = document.getElementById('board-select');
    const topicInput = document.getElementById('topic-input');
    const agentSelect = document.getElementById('agent-select-community');
    const runStatus = document.getElementById('run-status');
    const batchStatus = document.getElementById('batch-status');
    const postList = document.getElementById('post-list');
    const batchNameInput = document.getElementById('batch-name-input');
    const agentCountInput = document.getElementById('agent-count-input');
    const citizenTypeSelect = document.getElementById('citizen-type-select');
    const batchResultDiv = document.getElementById('batch-result');

    function renderPost(post) {
        const card = document.createElement('article');
        card.className = 'post-card';

        const meta = document.createElement('div');
        meta.className = 'post-meta';
        const createdAt = post.created_at || '방금 생성됨';
        meta.textContent = `${post.board} | ${post.author_name} | ${createdAt}`;

        const title = document.createElement('h4');
        title.textContent = post.title;

        const content = document.createElement('p');
        content.textContent = post.content;

        card.appendChild(meta);
        card.appendChild(title);
        card.appendChild(content);

        if (post.source_topic) {
            const topic = document.createElement('div');
            topic.className = 'post-topic';
            topic.textContent = `주제: ${post.source_topic}`;
            card.appendChild(topic);
        }

        return card;
    }

    // 에이전트 리스트 로드
    async function loadAgents() {
        try {
            const response = await fetch('/community/agents');
            const data = await response.json();
            if (data.agents && data.agents.length > 0) {
                data.agents.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = `${agent.nickname} (영향력: ${agent.influence})`;
                    agentSelect.appendChild(option);
                });
            }
        } catch (error) {
            console.error('에이전트 리스트 로드 실패:', error);
        }
    }

    // 배치 생성
    async function generateBatch() {
        const citizenTypes = Array.from(citizenTypeSelect.selectedOptions).map(o => parseInt(o.value));
        const payload = {
            batch_name: batchNameInput.value.trim() || 'batch_default',
            count: parseInt(agentCountInput.value) || 10,
            region_code: 0,
            citizen_types: citizenTypes.length > 0 ? citizenTypes : [1, 2, 3],
            sumin_jobs: ['직장인', '학생', '공무원'],
            context_topic: '수민넷 커뮤니티',
        };

        generateBatchButton.disabled = true;
        batchStatus.textContent = '배치 생성 중...';
        batchResultDiv.style.display = 'none';

        try {
            const response = await fetch('/community/generate_batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || '배치 생성 실패');
            }

            // 결과 표시
            document.getElementById('batch-id').textContent = data.batch_id;
            document.getElementById('created-count').textContent = data.created_count;
            document.getElementById('total-count').textContent = data.total_requested;

            const agentListDiv = document.getElementById('created-agents');
            agentListDiv.innerHTML = '';
            data.created_agents.forEach(agent => {
                const item = document.createElement('p');
                item.textContent = `✓ ${agent.nickname} (ID: ${agent.id})`;
                agentListDiv.appendChild(item);
            });

            batchResultDiv.style.display = 'block';
            batchStatus.textContent = `완료: ${data.created_count}/${data.total_requested} 에이전트 생성됨`;

            // 에이전트 리스트 새로고침
            agentSelect.innerHTML = '<option value="">- 에이전트 선택 -</option>';
            loadAgents();
        } catch (error) {
            batchStatus.textContent = `오류: ${error.message}`;
        } finally {
            generateBatchButton.disabled = false;
        }
    }

    async function runPipelineOnce() {
        const payload = {
            board: boardSelect.value,
            topic: topicInput.value.trim() || '오늘의 주요 이슈',
            agent_id: agentSelect.value,
        };

        if (!payload.agent_id) {
            runStatus.textContent = '오류: 에이전트를 선택해주세요';
            return;
        }

        runButton.disabled = true;
        runStatus.textContent = '파이프라인 실행 중...';

        try {
            const response = await fetch('/community/run_once', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || '실행 실패');
            }

            const emptyMessage = postList.querySelector('.empty-posts');
            if (emptyMessage) {
                emptyMessage.remove();
            }

            const card = renderPost(data.post);
            postList.prepend(card);
            runStatus.textContent = '완료: 게시글 1건 생성됨';
        } catch (error) {
            runStatus.textContent = `오류: ${error.message}`;
        } finally {
            runButton.disabled = false;
        }
    }

    // 초기 로드
    loadAgents();

    // 이벤트 리스너
    runButton.addEventListener('click', runPipelineOnce);
    generateBatchButton.addEventListener('click', generateBatch);
});
