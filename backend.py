"""
RoadWatch Kerala - Backend API with AI Moderation
This Flask app handles report submissions and uses Claude AI for moderation
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
from datetime import datetime
import json
import re

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize Claude client (you'll need to set your API key)
# Get your API key from: https://console.anthropic.com/
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
)

# In-memory storage (in production, use a real database like PostgreSQL)
reports = []
rejected_reports = []

# Kerala plate number validation regex
KERALA_PLATE_PATTERN = r'^KL-\d{2}-[A-Z]{1,2}-\d{1,4}$'


def validate_plate_number(plate):
    """Validate Kerala vehicle plate number format"""
    return bool(re.match(KERALA_PLATE_PATTERN, plate))


def moderate_report_with_ai(report_data):
    """
    TEMPORARY: Skip AI moderation for testing
    Remove this and use the real version once you add API credits
    """
    
    # Simple keyword check instead of AI
    description = report_data.get('description', '').lower()
    
    # Block obvious spam
    bad_words = ['idiot', 'stupid', 'hate', 'kill', 'beat']
    if any(word in description for word in bad_words):
        return (False, 'Contains inappropriate language', 0.8, ['abusive_language'])
    
    # Approve everything else
    return (True, 'Auto-approved (AI disabled for testing)', 0.5, [])


def check_duplicate_reports(plate_number, user_id, time_window_hours=24):
    """Check if the same user has reported this plate recently"""
    recent_reports = [
        r for r in reports 
        if r['plateNumber'] == plate_number 
        and r.get('userId') == user_id
        and (datetime.now() - datetime.fromisoformat(r['timestamp'])).seconds < time_window_hours * 3600
    ]
    return len(recent_reports)


@app.route('/api/reports', methods=['POST'])
def submit_report():
    """Handle new report submission"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['plateNumber', 'violations', 'location']
        for field in required_fields:
            if field not in data or not data[field]:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate plate number format
        plate_number = data['plateNumber'].upper()
        if not validate_plate_number(plate_number):
            return jsonify({'error': 'Invalid Kerala plate number format'}), 400
        
        # Check for duplicate reports from same user
        user_id = data.get('userId', request.remote_addr)  # Use IP if no user ID
        duplicate_count = check_duplicate_reports(plate_number, user_id)
        
        if duplicate_count >= 3:
            return jsonify({
                'error': 'You have already reported this vehicle multiple times today. Please wait before reporting again.',
                'reason': 'duplicate_prevention'
            }), 429
        
        # Add metadata
        report_data = {
            **data,
            'plateNumber': plate_number,
            'userId': user_id,
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        # AI Moderation
        is_approved, reason, confidence, flags = moderate_report_with_ai(report_data)
        
        report_data['moderation'] = {
            'approved': is_approved,
            'reason': reason,
            'confidence': confidence,
            'flags': flags,
            'reviewedAt': datetime.now().isoformat()
        }
        
        if is_approved:
            report_data['status'] = 'approved'
            reports.append(report_data)
            
            return jsonify({
                'success': True,
                'message': 'Report submitted and approved',
                'reportId': len(reports),
                'confidence': confidence
            }), 201
        else:
            report_data['status'] = 'rejected'
            rejected_reports.append(report_data)
            
            return jsonify({
                'success': False,
                'message': 'Report rejected by AI moderation',
                'reason': reason,
                'flags': flags,
                'note': 'If you believe this is an error, please contact support'
            }), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Get list of approved reports"""
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    
    # Sort by timestamp, newest first
    sorted_reports = sorted(
        [r for r in reports if r['status'] == 'approved'],
        key=lambda x: x['timestamp'],
        reverse=True
    )
    
    paginated_reports = sorted_reports[offset:offset + limit]
    
    return jsonify({
        'reports': paginated_reports,
        'total': len(sorted_reports),
        'limit': limit,
        'offset': offset
    })


@app.route('/api/reports/plate/<plate_number>', methods=['GET'])
def get_reports_by_plate(plate_number):
    """Get all reports for a specific plate number"""
    plate_number = plate_number.upper()
    
    plate_reports = [r for r in reports if r['plateNumber'] == plate_number and r['status'] == 'approved']
    
    # Calculate safety score based on reports
    violation_counts = {}
    for report in plate_reports:
        for violation in report['violations']:
            violation_counts[violation] = violation_counts.get(violation, 0) + 1
    
    return jsonify({
        'plateNumber': plate_number,
        'totalReports': len(plate_reports),
        'reports': plate_reports,
        'violationBreakdown': violation_counts,
        'safetyScore': max(0, 100 - (len(plate_reports) * 10))  # Simple scoring
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    total_reports = len(reports)
    approved_reports = len([r for r in reports if r['status'] == 'approved'])
    rejected_reports = len([r for r in reports if r['status'] == 'rejected'])
    
    today = datetime.now().date()
    today_reports = len([
        r for r in reports 
        if datetime.fromisoformat(r['timestamp']).date() == today
    ])
    
    return jsonify({
        'total': total_reports,
        'approved': approved_reports,
        'rejected': rejected_reports,
        'today': today_reports,
        'approvalRate': (approved_reports / total_reports * 100) if total_reports > 0 else 0
    })


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


if __name__ == '__main__':
    print("🚦 RoadWatch Kerala Backend Starting...")
    print("📝 Make sure to set ANTHROPIC_API_KEY environment variable")
    print("🌐 API will be available at http://localhost:5000")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
