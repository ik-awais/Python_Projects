"""Chat endpoint using RAG pipeline with session tracking and history."""
from flask import Blueprint, request, jsonify, current_app

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json() or {}
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'Missing "question" field'}), 400
    
    subject = data.get('subject') or None
    top_k = data.get('top_k', 5)
    session_id = data.get('session_id')
    
    # If no session_id is provided, generate a new one
    if not session_id:
        session_repo = current_app.config['SESSION_REPO']
        session_id = session_repo.create()
    
    # Generate RAG answer
    rag = current_app.config['RAG_PIPELINE']
    result = rag.answer(question, subject, top_k)
    
    # Record this exchange to the database/repository
    conv_repo = current_app.config['CONVERSATION_REPO']
    conv_repo.create(session_id, question, result.get('answer', ''))
    
    # Append the session_id to the response payload for the client
    result['session_id'] = session_id
    return jsonify(result)

@chat_bp.route('/chat/history', methods=['GET'])
def history():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({'error': 'Missing session_id'}), 400
        
    conv_repo = current_app.config['CONVERSATION_REPO']
    history_records = conv_repo.get_by_session(session_id, limit=50)
    
    return jsonify({
        'session_id': session_id, 
        'history': history_records
    })