from flask import Blueprint, current_app, jsonify, render_template, request, session, url_for, redirect

community_bp = Blueprint('community', __name__)

BOARD_GROUPS = {
    '유머/자유': ['자유'],
    '지역별 커뮤니티': ['성서구', '성동구', '성남구', '성내구', '성북구', '관북·청도'],
    '직업별': ['학생', '군인', '직장인', '공무원'],
    '분야별 특화': ['정치', '주식/경제', '과학/학문', '여행/문화'],
}

BEST_MIN_UPVOTES = 12


def _require_auth():
    if not session.get('authenticated'):
        return False
    return True


def _get_board_list():
    boards = []
    for group_boards in BOARD_GROUPS.values():
        boards.extend(group_boards)
    return boards


def _get_board_group(board_name):
    for group_name, boards in BOARD_GROUPS.items():
        if board_name in boards:
            return group_name
    return '기타'


def _get_display_posts(posts):
    display_posts = []
    for post in posts:
        item = dict(post)
        item['board_group'] = _get_board_group(item.get('board', ''))
        item['flair'] = item.get('flair') or '일반'
        item['upvote_count'] = item.get('upvote_count', 0) or 0
        item['downvote_count'] = item.get('downvote_count', 0) or 0
        item['view_count'] = item.get('view_count', 0) or 0
        display_posts.append(item)
    return display_posts


def _render_community_page(active_board=None, detail_post=None, sort_mode='best'):
    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    agent_repository = current_app.config.get('AGENT_REPOSITORY')

    posts = repository.get_recent(limit=200, board=active_board, sort=sort_mode) if repository else []
    if sort_mode == 'best':
        posts = [post for post in posts if (post.get('upvote_count') or 0) >= BEST_MIN_UPVOTES]
    model_presets = current_app.config.get('MODEL_PRESETS', {})
    agents = agent_repository.get_all_agents(status=1, limit=100) if agent_repository else []
    boards = _get_board_list()
    display_posts = _get_display_posts(posts)

    return render_template(
        'community.html',
        posts=display_posts,
        boards=boards,
        board_groups=BOARD_GROUPS,
        model_presets=model_presets,
        agents=agents,
        active_board=active_board,
        active_group=_get_board_group(active_board) if active_board else None,
        active_sort=sort_mode,
        detail_post=detail_post,
        detail_only=detail_post is not None,
    )


@community_bp.route('/community')
def community_page():
    if not _require_auth():
        return redirect(url_for('auth.index'))
    return _render_community_page(active_board=None, sort_mode='best')


@community_bp.route('/community/latest')
def community_latest():
    if not _require_auth():
        return redirect(url_for('auth.index'))
    return _render_community_page(active_board=None, sort_mode='latest')


@community_bp.route('/community/board/<path:board_name>')
def community_board(board_name):
    if not _require_auth():
        return redirect(url_for('auth.index'))

    sort_mode = request.args.get('sort', default='best')
    return _render_community_page(active_board=board_name, sort_mode=sort_mode)


@community_bp.route('/community/post/<int:post_id>')
def community_post_detail(post_id):
    if not _require_auth():
        return redirect(url_for('auth.index'))

    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    post = None
    if repository:
        post = repository.get_post(post_id)
        if post:
            repository.increment_post_view(post_id)
            post = repository.get_post(post_id)

    return _render_community_page(active_board=(post['board'] if post else None), detail_post=post, sort_mode='latest')


@community_bp.route('/community/run_once', methods=['POST'])
def run_once():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    board = (data.get('board') or '자유').strip()
    topic = (data.get('topic') or '오늘의 주요 이슈').strip()
    agent_id = (data.get('agent_id') or '').strip()

    if not agent_id:
        return jsonify({'error': 'agent_id is required'}), 400

    agent_repo = current_app.config.get('AGENT_REPOSITORY')
    if agent_repo is None:
        return jsonify({'error': 'Agent repository not configured'}), 500

    agent = agent_repo.get_agent(agent_id)
    if not agent:
        return jsonify({'error': 'Agent not found'}), 404

    model_presets = current_app.config.get('MODEL_PRESETS', {})
    model_preset = next(iter(model_presets.values()), None)
    if not model_preset:
        return jsonify({'error': 'Model preset not found'}), 400

    pipeline = current_app.config.get('COMMUNITY_PIPELINE_SERVICE')
    if pipeline is None:
        return jsonify({'error': 'Pipeline service not configured'}), 500

    result = pipeline.run_once(board=board, topic=topic, model_preset=model_preset, author_name=agent['nickname'])
    return jsonify({'post': result})


@community_bp.route('/community/posts', methods=['GET'])
def get_posts():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    board = request.args.get('board')
    limit = request.args.get('limit', default=30, type=int)

    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    if repository is None:
        return jsonify({'posts': []})

    sort_mode = request.args.get('sort', default='latest')
    posts = repository.get_recent(limit=max(1, min(limit, 100)), board=board, sort=sort_mode)
    return jsonify({'posts': posts})


@community_bp.route('/community/post/<int:post_id>/vote', methods=['POST'])
def vote_post(post_id):
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json(silent=True) or request.form or {}
    vote_type = (data.get('vote_type') or 'up').strip()

    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    if repository is None:
        return jsonify({'error': 'Post repository not configured'}), 500

    success = repository.vote_post(post_id, vote_type)
    if not success:
        return jsonify({'error': 'Vote failed'}), 500

    post = repository.get_post(post_id)
    if request.is_json:
        return jsonify({'ok': True, 'post': post})

    return redirect(request.referrer or url_for('community.community_post_detail', post_id=post_id))


@community_bp.route('/community/agents', methods=['GET'])
def get_agents():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    agent_repo = current_app.config.get('AGENT_REPOSITORY')
    if agent_repo is None:
        return jsonify({'agents': []})
    agents = agent_repo.get_all_agents(status=1, limit=100)
    return jsonify({'agents': agents})


@community_bp.route('/community/generate_batch', methods=['POST'])
def generate_batch():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.get_json() or {}
    batch_name = (data.get('batch_name') or 'default').strip()
    count = data.get('count', 10)
    region_code = data.get('region_code', 0)
    citizen_types = data.get('citizen_types', [1, 2, 3])
    sumin_jobs = data.get('sumin_jobs', ['직장인', '학생', '공무원'])
    context_topic = data.get('context_topic', '수민넷 커뮤니티')
    if not isinstance(count, int) or count < 1 or count > 100:
        return jsonify({'error': 'Invalid count (1-100)'}), 400
    generator = current_app.config.get('AGENT_GENERATOR_SERVICE')
    if generator is None:
        return jsonify({'error': 'Agent generator service not configured'}), 500
    try:
        result = generator.generate_batch(
            batch_name=batch_name,
            count=count,
            region_code=region_code,
            citizen_types=citizen_types,
            sumin_jobs=sumin_jobs,
            context_topic=context_topic,
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
