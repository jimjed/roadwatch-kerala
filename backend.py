"""
RoadWatch Kerala - Backend API with AI Moderation
This Flask app handles report submissions and uses Claude AI for moderation
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import httpx
import os
from datetime import datetime, timedelta
import json
import re
from models import db, Report

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Initialize Claude client (you'll need to set your API key)
# Get your API key from: https://console.anthropic.com/
#
#
# The official `anthropic` client library constructs an `httpx.Client`
# instance internally and passes a `proxies` keyword argument.  older
# versions of `httpx` (and the version currently pulled in by the
# Heroku/Container build) do **not** expose a `proxies` parameter; the
# argument was renamed to `proxy` in 0.24 and removed in later
# releases.  if a mismatched combination of `anthropic` and `httpx`
# ends up on the image we see errors like::
#
#     TypeError: Client.__init__() got an unexpected keyword argument
#     'proxies'
#
# To make the application robust against whatever version of `httpx`
# happens to be installed in the container, monkey‑patch the client
# constructor so that it accepts `proxies` and forwards it to the
# correct parameter name.  this is a small compatibility shim and
# keeps us from having to pin `httpx` very tightly in requirements.

# patch httpx.Client before creating the Anthropiс client
_orig_httpx_client_init = httpx.Client.__init__

def _httpx_init_with_proxies(self, *args, proxies=None, **kwargs):
    # the new httpx versions expect `proxy` (singular); older ones
    # don't even know what a proxies kwarg is.  convert if present.
    if proxies is not None:
        # avoid overwriting an explicit proxy arg if one is already
        # provided for some reason
        kwargs.setdefault("proxy", proxies)
    return _orig_httpx_client_init(self, *args, **kwargs)

httpx.Client.__init__ = _httpx_init_with_proxies

# Database configuration
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    # Railway uses postgres:// but SQLAlchemy needs postgresql://
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL or 'sqlite:///roadwatch.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database
db.init_app(app)

# Initialize Claude client (you'll need to set your API key)
# Get your API key from: https://console.anthropic.com/
client = anthropic.Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "YOUR_API_KEY_HERE")
)

# Create database tables
with app.app_context():
    db.create_all()
    print("✅ Database tables created successfully")

# Kerala plate number validation regex
KERALA_PLATE_PATTERN = r'^KL-\d{2}-[A-Z]{1,2}-\d{1,4}$'


def validate_plate_number(plate):
    """Validate Kerala vehicle plate number format"""
    return bool(re.match(KERALA_PLATE_PATTERN, plate))


def moderate_report_with_ai(report_data):
    """
    Use Claude AI to moderate the report for spam, abuse, and legitimacy
    Returns: (is_approved, reason, confidence_score)
    """
    
    prompt = f"""You are a traffic violation report moderator for Kerala, India. 
Review this report and determine if it's legitimate or should be rejected.

Report Details:
- Plate Number: {report_data['plateNumber']}
- Violations: {', '.join(report_data['violations'])}
- Location: {report_data['location']}
- Description: {report_data['description']}
- Submitted by User ID: {report_data.get('userId', 'anonymous')}

Check for these red flags:
1. **Personal vendetta**: Same user repeatedly reporting the same plate
2. **Vague/non-specific**: Generic complaints without clear violation
3. **Abusive language**: Slurs, threats, or hate speech in Hindi/English/Malayalam
4. **Spam patterns**: Multiple similar reports in short time
5. **Impossible violations**: Contradictory or physically impossible claims

Respond in JSON format:
{{
    "approved": true/false,
    "reason": "Brief explanation for your decision",
    "confidence": 0.0-1.0,
    "flags": ["list", "of", "issues", "found"]
}}"""

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        # Parse Claude's response
        response_text = message.content[0].text
        
        # Extract JSON from response (Claude might wrap it in markdown)
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            moderation_result = json.loads(json_match.group())
            return (
                moderation_result.get('approved', False),
                moderation_result.get('reason', 'AI moderation completed'),
                moderation_result.get('confidence', 0.5),
                moderation_result.get('flags', [])
            )
        else:
            # Fallback if JSON parsing fails
            return (True, 'Unable to parse AI response, approved by default', 0.5, [])
            
    except Exception as e:
        print(f"AI moderation error: {e}")
        # In case of API error, we could either reject by default (safe)
        # or approve by default (user-friendly). Let's approve but flag for manual review
        return (True, f'AI unavailable, flagged for manual review: {str(e)}', 0.3, ['ai_error'])


def check_duplicate_reports(plate_number, user_id, time_window_hours=24):
    """Check if the same user has reported this plate recently"""
    cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
    
    recent_reports = Report.query.filter(
        Report.plate_number == plate_number,
        Report.user_id == user_id,
        Report.created_at >= cutoff_time
    ).count()
    
    return recent_reports


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
        
        # Create new report
        report = Report(
            plate_number=plate_number,
            violations=data['violations'],
            location=data['location'],
            description=data.get('description'),
            photo_url=data.get('photoUrl'),
            user_id=user_id
        )
        
        # Prepare data for AI moderation
        report_data = {
            'plateNumber': plate_number,
            'violations': data['violations'],
            'location': data['location'],
            'description': data.get('description', ''),
            'userId': user_id
        }
        
        # AI Moderation
        is_approved, reason, confidence, flags = moderate_report_with_ai(report_data)
        
        # Set moderation results
        report.set_moderation(is_approved, reason, confidence, flags)
        
        # Save to database
        db.session.add(report)
        db.session.commit()
        
        if is_approved:
            return jsonify({
                'success': True,
                'message': 'Report submitted and approved',
                'reportId': report.id,
                'confidence': confidence
            }), 201
        else:
            return jsonify({
                'success': False,
                'message': 'Report rejected by AI moderation',
                'reason': reason,
                'flags': flags,
                'note': 'If you believe this is an error, please contact support'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"Error submitting report: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/reports', methods=['GET'])
def get_reports():
    """Get list of approved reports"""
    limit = int(request.args.get('limit', 10))
    offset = int(request.args.get('offset', 0))
    
    # Query approved reports, newest first
    reports_query = Report.query.filter_by(status='approved').order_by(Report.created_at.desc())
    
    total = reports_query.count()
    paginated_reports = reports_query.limit(limit).offset(offset).all()
    
    return jsonify({
        'reports': [r.to_dict() for r in paginated_reports],
        'total': total,
        'limit': limit,
        'offset': offset
    })


@app.route('/api/reports/plate/<plate_number>', methods=['GET'])
def get_reports_by_plate(plate_number):
    """Get all reports for a specific plate number"""
    plate_number = plate_number.upper()
    
    plate_reports = Report.query.filter_by(
        plate_number=plate_number,
        status='approved'
    ).order_by(Report.created_at.desc()).all()
    
    # Calculate safety score based on reports
    violation_counts = {}
    for report in plate_reports:
        violations = json.loads(report.violations) if report.violations else []
        for violation in violations:
            violation_counts[violation] = violation_counts.get(violation, 0) + 1
    
    return jsonify({
        'plateNumber': plate_number,
        'totalReports': len(plate_reports),
        'reports': [r.to_dict() for r in plate_reports],
        'violationBreakdown': violation_counts,
        'safetyScore': max(0, 100 - (len(plate_reports) * 10))  # Simple scoring
    })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get overall statistics"""
    total_reports = Report.query.count()
    approved_reports = Report.query.filter_by(status='approved').count()
    rejected_reports = Report.query.filter_by(status='rejected').count()
    
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())
    today_reports = Report.query.filter(Report.created_at >= today_start).count()
    
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
    
    # Use PORT from environment (for deployment platforms) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 API will be available at http://0.0.0.0:{port}")
    
    app.run(debug=False, host='0.0.0.0', port=port)
