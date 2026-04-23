# app.py
from flask import Flask
from flask_cors import CORS
import logging
from config import LOG_LEVEL, SECRET_KEY, CLOVA_HOST, CLOVA_API_KEY, CLOVA_PRIMARY_KEY, CLOVA_REQUEST_ID, MAX_MEMORY_LENGTH
from setup import initialize
from db import init_db, close_db
from routes.auth import auth_bp
from routes.chat import chat_bp
from routes.community import community_bp
from routes.admin import admin_bp
from models.vector_store_manager import VectorStoreManager
from models.completion_executor import CompletionExecutor
from services.adapters import CompletionExecutorClient, SqliteCommunityPostRepository, VectorStoreContextProvider
from services.chat_service import ChatService
from services.community_pipeline_service import CommunityPipelineService
from services.conversation_store import FlaskSessionConversationStore

# 초기 설정 및 로드
all_example_questions, model_presets = initialize()

# Flask 애플리케이션 설정
app = Flask(__name__)
CORS(app)
app.secret_key = SECRET_KEY

# 설정을 app.config에 저장
app.config['MODEL_PRESETS'] = model_presets
app.config['ALL_EXAMPLE_QUESTIONS'] = all_example_questions

# 로그 설정
logging.basicConfig(level=getattr(logging, LOG_LEVEL), format='[%(levelname)s] %(message)s')

# 벡터 스토어 관리자 초기화
vector_store_manager = VectorStoreManager()
vector_store_manager.get_vector_store()
app.config['VECTOR_STORE_MANAGER'] = vector_store_manager

# 클로바 실행기 초기화
completion_executor = CompletionExecutor(
    host=CLOVA_HOST,
    api_key=CLOVA_API_KEY,
    api_key_primary_val=CLOVA_PRIMARY_KEY,
    request_id=CLOVA_REQUEST_ID
)
app.config['COMPLETION_EXECUTOR'] = completion_executor
app.config['CONVERSATION_STORE'] = FlaskSessionConversationStore()
app.config['CONTEXT_PROVIDER'] = VectorStoreContextProvider(vector_store_manager)
app.config['LLM_CLIENT'] = CompletionExecutorClient(completion_executor)
app.config['COMMUNITY_POST_REPOSITORY'] = SqliteCommunityPostRepository()
app.config['CHAT_SERVICE'] = ChatService(
    app.config['CONTEXT_PROVIDER'],
    app.config['LLM_CLIENT'],
    app.config['CONVERSATION_STORE'],
    MAX_MEMORY_LENGTH,
)
app.config['COMMUNITY_PIPELINE_SERVICE'] = CommunityPipelineService(
    app.config['CONTEXT_PROVIDER'],
    app.config['LLM_CLIENT'],
    app.config['COMMUNITY_POST_REPOSITORY'],
)

# 블루프린트 등록
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(community_bp)
app.register_blueprint(admin_bp)

# 데이터베이스 초기화
def _setup():
    init_db()
    
app.before_request(_setup)

# 데이터베이스 연결 종료
app.teardown_appcontext(close_db)

if __name__ == '__main__':
    app.run(debug=True)
