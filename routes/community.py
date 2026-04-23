from flask import Blueprint, current_app, jsonify, render_template, request, session, url_for, redirect

community_bp = Blueprint('community', __name__)


def _require_auth():
    if not session.get('authenticated'):
        return False
    return True


def _get_board_list():
    return [
        '통합 광장',
        '정치',
        '주식/경제',
        '과학/학문',
        '여행/문화',
        '성내구',
        '성동구',
        '성북구',
        '직장인',
        '공무원',
    ]


def _render_community_page(active_board=None, detail_post=None):
    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    agent_repository = current_app.config.get('AGENT_REPOSITORY')

    posts = repository.get_recent(limit=100, board=active_board) if repository else []
    model_presets = current_app.config.get('MODEL_PRESETS', {})
    agents = agent_repository.get_all_agents(status=1, limit=100) if agent_repository else []
    boards = _get_board_list()

    return render_template(
        'community.html',
        posts=posts,
        boards=boards,
        model_presets=model_presets,
        agents=agents,
        active_board=active_board or '통합 광장',
        detail_post=detail_post,
    )


@community_bp.route('/community')
def community_page():
    if not _require_auth():
        return redirect(url_for('auth.index'))
    return _render_community_page(active_board='통합 광장')


@community_bp.route('/community/board/<board_name>')
def community_board(board_name):
    if not _require_auth():
        return redirect(url_for('auth.index'))

    return _render_community_page(active_board=board_name)


@community_bp.route('/community/post/<int:post_id>')
def community_post_detail(post_id):
    if not _require_auth():
        return redirect(url_for('auth.index'))

    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    post = None
    if repository:
        recent_posts = repository.get_recent(limit=500)
        for item in recent_posts:
            if item.get('id') == post_id:
                post = item
                break

    return _render_community_page(active_board=(post['board'] if post else '통합 광장'), detail_post=post)


@community_bp.route('/community/run_once', methods=['POST'])
def run_once():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    board = (data.get('board') or '통합 광장').strip()
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

    posts = repository.get_recent(limit=max(1, min(limit, 100)), board=board)
    return jsonify({'posts': posts})


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
