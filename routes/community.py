from flask import Blueprint, current_app, jsonify, render_template, request, session, url_for, redirect

community_bp = Blueprint('community', __name__)


def _require_auth():
    if not session.get('authenticated'):
        return False
    return True


@community_bp.route('/community')
def community_page():
    if not _require_auth():
        return redirect(url_for('auth.index'))

    repository = current_app.config.get('COMMUNITY_POST_REPOSITORY')
    posts = repository.get_recent(limit=30) if repository else []
    model_presets = current_app.config.get('MODEL_PRESETS', {})

    boards = [
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

    return render_template('community.html', posts=posts, boards=boards, model_presets=model_presets)


@community_bp.route('/community/run_once', methods=['POST'])
def run_once():
    if not _require_auth():
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    board = (data.get('board') or '통합 광장').strip()
    topic = (data.get('topic') or '오늘의 주요 이슈').strip()
    model_key = (data.get('model') or 'model1').strip()

    model_presets = current_app.config.get('MODEL_PRESETS', {})
    model_preset = model_presets.get(model_key, model_presets.get('model1'))
    if not model_preset:
        return jsonify({'error': 'Model preset not found'}), 400

    pipeline = current_app.config.get('COMMUNITY_PIPELINE_SERVICE')
    if pipeline is None:
        return jsonify({'error': 'Pipeline service not configured'}), 500

    result = pipeline.run_once(board=board, topic=topic, model_preset=model_preset)
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
