let currentPost = null;

document.addEventListener('DOMContentLoaded', function () {
    loadAgents();
});

// 에이전트 리스트 로드
async function loadAgents() {
    try {
        const response = await fetch('/community/agents');
        const data = await response.json();
        const select = document.getElementById('agent-select-community');
        select.innerHTML = '<option value="">- 에이전트 선택 -</option>';
        
        if (data.agents && data.agents.length > 0) {
            data.agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.id;
                option.textContent = `${agent.nickname} (영향력: ${agent.influence})`;
                select.appendChild(option);
            });
        }
    } catch (error) {
        console.error('에이전트 리스트 로드 실패:', error);
    }
}

// 배치 생성
async function generateBatch() {
    const batchName = document.getElementById('batch-name-input').value.trim() || 'batch_1';
    const count = parseInt(document.getElementById('agent-count-input').value) || 5;
    const citizenTypeSelect = document.getElementById('citizen-type-select');
    const citizenTypes = Array.from(citizenTypeSelect.selectedOptions).map(o => parseInt(o.value));
    const status = document.getElementById('batch-status');
    const result = document.getElementById('batch-result');

    if (!citizenTypes.length) {
        status.textContent = '⚠️ 시민 유형을 선택하세요';
        return;
    }

    status.textContent = '⏳ 배치 생성 중...';
    result.style.display = 'none';

    try {
        const response = await fetch('/community/generate_batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                batch_name: batchName,
                count: count,
                region_code: 0,
                citizen_types: citizenTypes,
                sumin_jobs: ['직장인', '학생', '공무원', '자영업자', '전문가'],
                context_topic: '수민넷 커뮤니티'
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '배치 생성 실패');
        }

        document.getElementById('created-count').textContent = data.created_count;
        document.getElementById('total-count').textContent = data.total_requested;
        result.style.display = 'block';
        status.textContent = `✓ 완료: 배치 ID ${data.batch_id}`;

        // 에이전트 리스트 새로고침
        await loadAgents();
    } catch (error) {
        status.textContent = `❌ ${error.message}`;
        console.error(error);
    }
}

// 1회 테스트 실행
async function runPipelineOnce() {
    const agentId = document.getElementById('agent-select-community').value;
    const board = document.getElementById('board-select').value;
    const topic = document.getElementById('topic-input').value.trim();
    const status = document.getElementById('run-status');

    if (!agentId) {
        status.textContent = '⚠️ 에이전트를 선택하세요';
        return;
    }

    status.textContent = '⏳ 실행 중...';

    try {
        const response = await fetch('/community/run_once', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                board: board,
                topic: topic,
                agent_id: agentId
            })
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || '실행 실패');
        }

        status.textContent = '✓ 게시글 생성됨!';
        
        // 테이블에 새 행 추가
        const tbody = document.getElementById('posts-tbody');
        const post = data.post;
        const row = document.createElement('tr');
        row.onclick = function() { openPostDetail(this, 1); };
        row.innerHTML = `
            <td class="col-num">1</td>
            <td class="col-tag"><span class="tag">${post.board.substring(0, 2)}</span></td>
            <td class="col-title">${post.title}</td>
            <td class="col-author">${post.author_name}</td>
            <td class="col-time">방금</td>
            <td class="col-views">1</td>
            <td class="col-like">0</td>
        `;
        row.dataset.post = JSON.stringify(post);
        tbody.insertBefore(row, tbody.firstChild);

        // 행 번호 재계산
        updateRowNumbers();
    } catch (error) {
        status.textContent = `❌ ${error.message}`;
        console.error(error);
    }
}

// 게시글 상세 보기
function openPostDetail(rowElement, index) {
    const modal = document.getElementById('post-modal');
    const cells = rowElement.querySelectorAll('td');
    
    let post = null;
    if (rowElement.dataset.post) {
        post = JSON.parse(rowElement.dataset.post);
    } else {
        // 테이블에서 직접 파싱
        post = {
            board: cells[1].textContent || '게시판',
            title: cells[2].textContent,
            author_name: cells[3].textContent,
            created_at: cells[4].textContent,
            content: '게시글 내용을 불러올 수 없습니다.',
            id: index
        };
    }

    document.getElementById('modal-title').textContent = post.title;
    document.getElementById('modal-meta').innerHTML = `
        <span>[${post.board}]</span>
        <span> | ${post.author_name}</span>
        <span> | ${post.created_at}</span>
    `;
    document.getElementById('modal-body').textContent = post.content;
    
    currentPost = post;
    modal.classList.add('active');
}

// 게시글 상세 닫기
function closePostDetail() {
    const modal = document.getElementById('post-modal');
    modal.classList.remove('active');
}

// 모달 외부 클릭 시 닫기
document.addEventListener('click', function(event) {
    const modal = document.getElementById('post-modal');
    if (event.target === modal) {
        modal.classList.remove('active');
    }
});

// 추천/비추천
function votePost(type) {
    const modal = document.getElementById('post-modal');
    if (type === 'up') {
        alert('추천했습니다! 👍');
    } else {
        alert('비추천했습니다. 👎');
    }
}

// 필터
function filterPosts(type) {
    console.log('필터:', type);
    // 향후 구현: 게시글 필터링
}

// 행 번호 업데이트
function updateRowNumbers() {
    const tbody = document.getElementById('posts-tbody');
    const rows = tbody.querySelectorAll('tr');
    rows.forEach((row, index) => {
        row.querySelector('.col-num').textContent = rows.length - index;
    });
}

window.loadAgents = loadAgents;
window.generateBatch = generateBatch;
window.runPipelineOnce = runPipelineOnce;
window.openPostDetail = openPostDetail;
window.closePostDetail = closePostDetail;
window.votePost = votePost;
window.filterPosts = filterPosts;
