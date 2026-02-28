"""
RoadWatch Kerala - Backend API with AI Moderation and User Authentication
This Flask app handles report submissions, uses Claude AI for moderation, and manages user authentication
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import anthropic
import os
from datetime import datetime, timedelta, timezone
import json
import re
from models import db, Report
from user_model import User
from auth import verify_firebase_token, require_auth, optional_auth

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

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


@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register or update user from Firebase authentication"""
    try:
        # Get token from request
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Missing authorization header'}), 401
        
        token = auth_header.split('Bearer ')[1]
        user_data = verify_firebase_token(token)
        
        if not user_data:
            return jsonify({'error': 'Invalid token'}), 401
        
        # Check if user exists
        user = User.query.filter_by(firebase_uid=user_data['uid']).first()
        
        if user:
            # Update existing user
            user.display_name = user_data.get('display_name', user.display_name)
            user.photo_url = user_data.get('photo_url', user.photo_url)
            user.last_login = utc_now()
            db.session.commit()
            
            return jsonify({
                'message': 'User updated',
                'user': user.to_dict()
            }), 200
        else:
            # Create new user
            user = User(
                firebase_uid=user_data['uid'],
                email=user_data['email'],
                display_name=user_data.get('display_name'),
                photo_url=user_data.get('photo_url')
            )
            db.session.add(user)
            db.session.commit()
            
            return jsonify({
                'message': 'User registered successfully',
                'user': user.to_dict()
            }), 201
            
    except Exception as e:
        db.session.rollback()
        print(f"Error registering user: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/profile', methods=['GET'])
@require_auth
def get_profile():
    """Get current user's profile"""
    try:
        user = User.query.filter_by(firebase_uid=request.current_user['uid']).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(user.to_dict()), 200
        
    except Exception as e:
        print(f"Error getting profile: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/auth/reports', methods=['GET'])
@require_auth
def get_user_reports():
    """Get current user's report history"""
    try:
        user = User.query.filter_by(firebase_uid=request.current_user['uid']).first()
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Get user's reports
        reports = Report.query.filter_by(user_id=user.id).order_by(Report.created_at.desc()).all()
        
        return jsonify({
            'user': user.to_dict(),
            'reports': [r.to_dict() for r in reports]
        }), 200
        
    except Exception as e:
        print(f"Error getting user reports: {e}")
        return jsonify({'error': str(e)}), 500


def utc_now():
    """Helper function to get current UTC time"""
    return datetime.now(timezone.utc)


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
- Description: {report_data['description'] or '(No description provided)'}
- Submitted by User ID: {report_data.get('userId', 'anonymous')}

IMPORTANT GUIDELINES:
- **Descriptions are OPTIONAL** - A report with violation type + location is sufficient
- **Empty/missing descriptions are acceptable** - Don't flag as vague if violation type is selected
- Only reject if there's clear abuse, spam, or impossible claims

Check for these red flags ONLY:
1. **Personal vendetta**: Same user repeatedly reporting the same plate
2. **Abusive language**: Slurs, threats, or hate speech in Hindi/English/Malayalam
3. **Spam patterns**: Multiple similar reports in short time
4. **Impossible violations**: Contradictory claims (e.g., "No helmet" for a car)

DO NOT reject for:
- Missing or short descriptions
- Generic violation reports (they selected a violation type, that's enough)
- Reports that just state facts without elaboration

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


def check_duplicate_reports(plate_number, user_identifier, is_authenticated=False, time_window_hours=24):
    """Check if the same user has reported this plate recently"""
    from datetime import timezone
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=time_window_hours)
    
    if is_authenticated:
        # user_identifier is user.id (integer)
        recent_reports = Report.query.filter(
            Report.plate_number == plate_number,
            Report.user_id == user_identifier,
            Report.created_at >= cutoff_time
        ).count()
    else:
        # user_identifier is IP address (string)
        recent_reports = Report.query.filter(
            Report.plate_number == plate_number,
            Report.user_ip == user_identifier,
            Report.created_at >= cutoff_time
        ).count()
    
    return recent_reports


@app.route('/api/reports', methods=['POST'])
@optional_auth
def submit_report():
    """Handle new report submission"""
    try:
        data = request.get_json()
        print(f"DEBUG: Received data: {data}")
        
        # Validate required fields
        required_fields = ['plateNumber', 'violations', 'location']
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"ERROR: Missing field: {field}")
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Validate plate number format
        plate_number = data['plateNumber'].upper()
        if not validate_plate_number(plate_number):
            print(f"ERROR: Invalid plate format: {plate_number}")
            return jsonify({'error': 'Invalid Kerala plate number format'}), 400
        
        # Get user if authenticated
        user = None
        user_identifier = request.remote_addr  # Fallback to IP
        is_authenticated = False
        
        if request.current_user:
            # User is authenticated
            user = User.query.filter_by(firebase_uid=request.current_user['uid']).first()
            
            if not user:
                # Create user if doesn't exist (shouldn't happen, but just in case)
                user = User(
                    firebase_uid=request.current_user['uid'],
                    email=request.current_user['email'],
                    display_name=request.current_user.get('display_name'),
                    photo_url=request.current_user.get('photo_url')
                )
                db.session.add(user)
                db.session.flush()  # Get user.id without committing
            
            # Check if user is banned
            if user.is_banned:
                return jsonify({
                    'error': 'Your account has been suspended',
                    'reason': user.ban_reason
                }), 403
            
            user_identifier = user.id
            is_authenticated = True
            print(f"DEBUG: Authenticated user: {user.email}")
        else:
            print(f"DEBUG: Anonymous user (IP: {request.remote_addr})")
        
        # Check for duplicate reports from same user
        print(f"DEBUG: Checking duplicates for user: {user_identifier}")
        duplicate_count = check_duplicate_reports(plate_number, user_identifier, is_authenticated)
        print(f"DEBUG: Duplicate count: {duplicate_count}")
        
        if duplicate_count >= 3:
            print(f"ERROR: Too many duplicates")
            return jsonify({
                'error': 'You have already reported this vehicle multiple times today. Please wait before reporting again.',
                'reason': 'duplicate_prevention'
            }), 429
        
        # Create new report
        print(f"DEBUG: Creating report object")
        report = Report(
            plate_number=plate_number,
            violations=data['violations'],
            location=data['location'],
            description=data.get('description'),
            photo_url=data.get('photoUrl'),
            user_id=user.id if user else None,
            user_ip=request.remote_addr if not user else None
        )
        
        # Prepare data for AI moderation
        report_data = {
            'plateNumber': plate_number,
            'violations': data['violations'],
            'location': data['location'],
            'description': data.get('description', ''),
            'userId': user.email if user else request.remote_addr
        }
        
        # AI Moderation
        print(f"DEBUG: Starting AI moderation")
        is_approved, reason, confidence, flags = moderate_report_with_ai(report_data)
        print(f"DEBUG: AI moderation returned approved={is_approved}, reason={reason}, confidence={confidence}, flags={flags}")
        
        # Set moderation results
        report.set_moderation(is_approved, reason, confidence, flags)
        
        # Update user stats if authenticated
        if user:
            user.update_stats(is_approved)
        
        # Save to database
        print(f"DEBUG: Attempting to save to database")
        db.session.add(report)
        db.session.commit()
        print(f"DEBUG: Successfully saved to database with ID: {report.id}")
        
        if is_approved:
            print(f"SUCCESS: Report approved and saved")
            return jsonify({
                'success': True,
                'message': 'Report submitted and approved',
                'reportId': report.id,
                'confidence': confidence
            }), 201
        else:
            print(f"INFO: Report rejected by AI moderation: {reason} (flags={flags})")
            return jsonify({
                'success': False,
                'message': 'Report rejected by AI moderation',
                'reason': reason,
                'flags': flags,
                'note': 'If you believe this is an error, please contact support'
            }), 400
            
    except Exception as e:
        db.session.rollback()
        print(f"EXCEPTION: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
    from datetime import timezone
    total_reports = Report.query.count()
    approved_reports = Report.query.filter_by(status='approved').count()
    rejected_reports = Report.query.filter_by(status='rejected').count()
    
    today = datetime.now(timezone.utc).date()
    today_start = datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
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
