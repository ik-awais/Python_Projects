"""Chat endpoint using RAG pipeline."""
from flask import Blueprint, request, jsonify, current_app

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    question = data.get('question', '').strip()
    if not question:
        return jsonify({'error': 'Missing "question" field'}), 400
    subject = data.get('subject', None)
    top_k = data.get('top_k', 5)

    rag = current_app.config['RAG_PIPELINE']
    result = rag.answer(question, subject, top_k)
    return jsonify(result)