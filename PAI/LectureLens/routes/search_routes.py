"""Search endpoint blueprint for hybrid search."""
from flask import Blueprint, request, jsonify, current_app

search_bp = Blueprint('search', __name__)

@search_bp.route('/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query parameter "q"'}), 400
    subject = request.args.get('subject', None)
    top_k = int(request.args.get('top_k', 5))

    search_service = current_app.config['SEARCH_SERVICE']
    results = search_service.hybrid_search(query, subject, top_k)
    return jsonify({'results': results})