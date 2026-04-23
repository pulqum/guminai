# routes/chat.py
from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for  # 'redirect' 추가
import random
import logging

chat_bp = Blueprint('chat', __name__)


def _get_chat_service():
    chat_service = current_app.config.get('CHAT_SERVICE')
    if chat_service is None:
        raise RuntimeError('CHAT_SERVICE is not configured')
    return chat_service

@chat_bp.route('/chat')
def chat_page():
    if not session.get('authenticated'):
        return redirect(url_for('auth.index'))
    
    # 모델 변경 시 세션 초기화
    session.pop('conversation_history', None)
    
    # 예시 질문 랜덤 선택
    num_questions = 3  # 표시할 질문의 수
    all_example_questions = current_app.config.get('ALL_EXAMPLE_QUESTIONS', [])
    example_questions = random.sample(all_example_questions, num_questions) if len(all_example_questions) >= num_questions else all_example_questions
    
    # 모델 정보 전달
    model_presets = current_app.config.get('MODEL_PRESETS', {})
    models = {
        model_key: {
            'display_name': model_info.get('display_name', model_key),
            'description': model_info.get('description', ''),
            'avatar_image': model_info.get('avatar_image', 'bot_avatar.png')
        } for model_key, model_info in model_presets.items()
    }
    
    return render_template('chat.html', models=models, example_questions=example_questions)

@chat_bp.route('/chat_api', methods=['POST'])
def chat_api_endpoint():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.get_json() or {}
    question = data.get('message', '').strip()

    # 사용자가 "test"라고 입력하면 정해진 테스트용 문장을 반환
    if question.lower() in ["test", "테스트", "ㅅㄷㄴㅅ"]:
        test_response = "이것은 테스트 응답입니다. 인공지능을 사용하지 않았습니다."
        return jsonify({'answer': test_response, 'reset_message': None})

    selected_model = data.get('model', 'model1')
    model_presets = current_app.config.get('MODEL_PRESETS', {})
    model_preset = model_presets.get(selected_model, model_presets.get('model1', {}))

    if not model_preset:
        return jsonify({'error': 'Model preset not found'}), 400

    try:
        chat_service = _get_chat_service()
        result = chat_service.handle_chat(question, model_preset)
        return jsonify(result)
    except Exception as e:
        logging.error(f"채팅 처리 중 오류 발생: {e}")
        return jsonify({'error': '채팅 처리 중 오류가 발생했습니다.'}), 500
    
@chat_bp.route('/map_data', methods=['POST'])
def map_data():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401

    # 요청에서 question 가져오기
    data = request.get_json() or {}
    question = data.get('question')
    chat_service = _get_chat_service()
    context = chat_service.get_map_context(question)

    # 결과 반환
    result = {"message": context}
    return jsonify(result)


@chat_bp.route('/get_example_questions', methods=['GET'])
def get_example_questions():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401

    num_questions = 3
    all_example_questions = current_app.config.get('ALL_EXAMPLE_QUESTIONS', [])
    example_questions = random.sample(all_example_questions, num_questions) if len(all_example_questions) >= num_questions else all_example_questions
    return jsonify({'example_questions': example_questions})


@chat_bp.route('/reset_conversation', methods=['POST'])
def reset_conversation():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401

    chat_service = _get_chat_service()
    chat_service.reset_conversation()
    return jsonify({'success': True})
