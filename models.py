"""
Database models for RoadWatch Kerala
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
import json

db = SQLAlchemy()

def utc_now():
    """Helper function to get current UTC time"""
    return datetime.now(timezone.utc)

class Report(db.Model):
    """Traffic violation report"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True)
    plate_number = db.Column(db.String(20), nullable=False, index=True)
    violations = db.Column(db.Text, nullable=False)  # JSON array as string
    location = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    photo_url = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # Link to User table
    user_ip = db.Column(db.String(50))  # Keep IP for backwards compatibility
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    
    # Moderation details
    moderation_approved = db.Column(db.Boolean, default=False)
    moderation_reason = db.Column(db.Text)
    moderation_confidence = db.Column(db.Float)
    moderation_flags = db.Column(db.Text)  # JSON array as string
    moderation_reviewed_at = db.Column(db.DateTime)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    updated_at = db.Column(db.DateTime, default=utc_now, onupdate=utc_now)
    
    def __init__(self, plate_number, violations, location, description=None, 
                 photo_url=None, user_id=None, user_ip=None, status='pending'):
        self.plate_number = plate_number
        self.violations = json.dumps(violations) if isinstance(violations, list) else violations
        self.location = location
        self.description = description
        self.photo_url = photo_url
        self.user_id = user_id
        self.user_ip = user_ip
        self.status = status
    
    def to_dict(self):
        """Convert report to dictionary for JSON response"""
        user_info = None
        if self.reporter:
            user_info = {
                'displayName': self.reporter.display_name,
                'photoUrl': self.reporter.photo_url,
                'reputationScore': self.reporter.reputation_score
            }
        
        return {
            'id': self.id,
            'plateNumber': self.plate_number,
            'violations': json.loads(self.violations) if self.violations else [],
            'location': self.location,
            'description': self.description,
            'photoUrl': self.photo_url,
            'user': user_info,
            'status': self.status,
            'moderation': {
                'approved': self.moderation_approved,
                'reason': self.moderation_reason,
                'confidence': self.moderation_confidence,
                'flags': json.loads(self.moderation_flags) if self.moderation_flags else [],
                'reviewedAt': self.moderation_reviewed_at.isoformat() if self.moderation_reviewed_at else None
            },
            'timestamp': self.created_at.isoformat(),
            'updatedAt': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def set_moderation(self, approved, reason, confidence, flags):
        """Set moderation results"""
        self.moderation_approved = approved
        self.moderation_reason = reason
        self.moderation_confidence = confidence
        self.moderation_flags = json.dumps(flags) if isinstance(flags, list) else flags
        self.moderation_reviewed_at = utc_now()
        self.status = 'approved' if approved else 'rejected'
    
    def __repr__(self):
        return f'<Report {self.id}: {self.plate_number}>'
