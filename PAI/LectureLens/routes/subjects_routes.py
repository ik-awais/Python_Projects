
"""Subjects endpoint to populate dropdown."""
from flask import Blueprint, jsonify, current_app
 
subjects_bp = Blueprint('subjects', __name__)
 
@subjects_bp.route('/subjects', methods=['GET'])
def get_subjects():
    subject_repo = current_app.config['SUBJECT_REPO']
    subjects = subject_repo.get_all()
    subject_names = [s['name'] for s in subjects]
    return jsonify(subject_names)