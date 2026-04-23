document.addEventListener('DOMContentLoaded', function () {
    const runButton = document.getElementById('run-once-button');
    const boardSelect = document.getElementById('board-select');
    const topicInput = document.getElementById('topic-input');
    const modelSelect = document.getElementById('model-select-community');
    const runStatus = document.getElementById('run-status');
    const postList = document.getElementById('post-list');

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

    async function runPipelineOnce() {
        const payload = {
            board: boardSelect.value,
            topic: topicInput.value.trim() || '오늘의 주요 이슈',
            model: modelSelect.value,
        };

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

    runButton.addEventListener('click', runPipelineOnce);
});
