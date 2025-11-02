"""
Database models for Solar Intelligence application
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

db = SQLAlchemy()


class User(UserMixin, db.Model):
    """User model with authentication, GDPR compliance, and usage tracking"""
    __tablename__ = 'user'
    __table_args__ = (
        db.Index('idx_user_username', 'username'),
        db.Index('idx_user_role', 'role'),
        db.Index('idx_user_created_at', 'created_at'),
        db.Index('idx_user_is_active', 'is_active'),
    )

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # GDPR Consent Tracking
    gdpr_consent_given = db.Column(db.Boolean, default=False, nullable=False)
    gdpr_consent_date = db.Column(db.DateTime)
    terms_accepted = db.Column(db.Boolean, default=False, nullable=False)
    terms_accepted_date = db.Column(db.DateTime)
    marketing_consent = db.Column(db.Boolean, default=False, nullable=False)
    marketing_consent_date = db.Column(db.DateTime)
    privacy_policy_version = db.Column(db.String(10), default='1.0')
    terms_version = db.Column(db.String(10), default='1.0')

    # Plan and Usage Tracking
    plan_type = db.Column(db.String(20), default='free')  # 'free' or 'premium'
    query_count = db.Column(db.Integer, default=0)  # Total queries made
    last_query_date = db.Column(db.DateTime)  # Last time user made a query
    plan_start_date = db.Column(db.DateTime)  # When current plan started
    plan_end_date = db.Column(db.DateTime)  # When plan expires (for premium)
    monthly_query_count = db.Column(db.Integer, default=0)  # Queries this month
    last_reset_date = db.Column(db.DateTime)  # Last monthly reset

    # Soft Delete for Account Deletion (30-day grace period)
    deleted = db.Column(db.Boolean, default=False, nullable=False)  # Soft delete flag
    deletion_requested_at = db.Column(db.DateTime)  # When deletion was requested
    deletion_reason = db.Column(db.Text)  # Optional: why user wants to delete

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)

    def set_password(self, password):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)

    def get_query_limit(self):
        """Get the query limit based on plan type, role, and survey bonuses"""
        # Admins have unlimited queries
        if self.role == 'admin':
            return float('inf')  # Unlimited for admins

        # Premium users get 1000 queries per month
        if self.plan_type == 'premium':
            return 1000

        # Free users: base 5 queries + survey bonuses
        base_limit = 5

        # Add bonus for Stage 1 survey completion
        if self.survey is not None:
            base_limit += self.survey.bonus_queries_granted

        # Add bonus for Stage 2 survey completion
        if self.survey_stage2 is not None:
            base_limit += self.survey_stage2.bonus_queries_granted

        return base_limit

    def can_make_query(self):
        """Check if user can make a query based on their plan limits

        NOTE: This method updates the user object but does NOT commit.
        The caller is responsible for committing the transaction.
        """
        # Reset monthly count if needed
        if self.last_reset_date is None or (datetime.utcnow() - self.last_reset_date).days >= 30:
            self.monthly_query_count = 0
            self.last_reset_date = datetime.utcnow()
            # Note: Not committing here - caller must commit

        return self.monthly_query_count < self.get_query_limit()

    def increment_query_count(self):
        """Increment query counters

        NOTE: This method updates the user object but does NOT commit.
        The caller is responsible for committing the transaction.
        """
        self.query_count += 1
        self.monthly_query_count += 1
        self.last_query_date = datetime.utcnow()
        # Note: Not committing here - caller must commit

    def get_usage_stats(self):
        """Get comprehensive usage statistics"""
        total_conversations = Conversation.query.filter_by(user_id=self.id).count()
        total_messages = Message.query.join(Conversation).filter(
            Conversation.user_id == self.id,
            Message.sender == 'user'
        ).count()

        return {
            'total_queries': self.query_count,
            'monthly_queries': self.monthly_query_count,
            'query_limit': self.get_query_limit(),
            'queries_remaining': self.get_query_limit() - self.monthly_query_count,
            'total_conversations': total_conversations,
            'total_messages': total_messages,
            'last_query_date': self.last_query_date,
            'account_age_days': (datetime.utcnow() - self.created_at).days if self.created_at else 0
        }


class Conversation(db.Model):
    """Conversation model for storing chat sessions"""
    __tablename__ = 'conversation'
    __table_args__ = (
        db.Index('idx_conversation_user_id', 'user_id'),
        db.Index('idx_conversation_created_at', 'created_at'),
        db.Index('idx_conversation_agent_type', 'agent_type'),
        db.Index('idx_conversation_user_created', 'user_id', 'created_at'),  # Composite index
    )

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    agent_type = db.Column(db.String(16), default='market')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    messages = db.relationship('Message', backref='conversation', lazy='dynamic')  # Changed to dynamic for better querying

    # Relationship to user
    user = db.relationship('User', backref=db.backref('conversations', lazy='dynamic'))


class Message(db.Model):
    """Message model for storing individual chat messages"""
    __tablename__ = 'message'
    __table_args__ = (
        db.Index('idx_message_conversation_id', 'conversation_id'),
        db.Index('idx_message_timestamp', 'timestamp'),
        db.Index('idx_message_sender', 'sender'),
        db.Index('idx_message_conv_timestamp', 'conversation_id', 'timestamp'),  # Composite index
    )

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender = db.Column(db.String(16))  # 'user' or 'bot'
    content = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class Waitlist(db.Model):
    """Model for waitlist email subscriptions"""
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    interested_agents = db.Column(db.Text, nullable=True)  # JSON string of agent preferences
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notified = db.Column(db.Boolean, default=False)
    notified_at = db.Column(db.DateTime)
    ip_address = db.Column(db.String(45))  # Support IPv6
    user_agent = db.Column(db.String(256))


class Feedback(db.Model):
    """Model for user feedback submissions"""
    __tablename__ = 'feedback'
    __table_args__ = (
        db.Index('idx_feedback_user_id', 'user_id'),
        db.Index('idx_feedback_created_at', 'created_at'),
        db.Index('idx_feedback_rating', 'rating'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    feedback_text = db.Column(db.Text, nullable=True)
    allow_followup = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(256))

    # Relationship to user
    user = db.relationship('User', backref=db.backref('feedbacks', lazy='dynamic'))


class UserSurvey(db.Model):
    """Model for user profiling survey responses - Stage 1"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    role = db.Column(db.String(50), nullable=False)
    role_other = db.Column(db.String(100), nullable=True)
    regions = db.Column(db.Text, nullable=False)  # JSON array of regions
    familiarity = db.Column(db.String(20), nullable=False)
    insights = db.Column(db.Text, nullable=False)  # JSON array of insight types
    tailored = db.Column(db.String(10), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bonus_queries_granted = db.Column(db.Integer, default=5)

    # Relationship to user
    user = db.relationship('User', backref=db.backref('survey', uselist=False, lazy=True))


class UserSurveyStage2(db.Model):
    """Model for user profiling survey responses - Stage 2 (Market Activity & Behaviour)"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    work_focus = db.Column(db.String(100), nullable=False)
    work_focus_other = db.Column(db.String(100), nullable=True)
    pv_segments = db.Column(db.Text, nullable=False)  # JSON array
    technologies = db.Column(db.Text, nullable=False)  # JSON array
    technologies_other = db.Column(db.String(200), nullable=True)
    challenges = db.Column(db.Text, nullable=False)  # JSON array of top 3
    weekly_insight = db.Column(db.Text, nullable=True)  # Open text response
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    bonus_queries_granted = db.Column(db.Integer, default=5)

    # Relationship to user
    user = db.relationship('User', backref=db.backref('survey_stage2', uselist=False, lazy=True))


class HiredAgent(db.Model):
    """Model for tracking which agents users have hired"""
    __tablename__ = 'hired_agent'
    __table_args__ = (
        db.UniqueConstraint('user_id', 'agent_type', name='unique_user_agent'),
        db.Index('idx_hired_agent_user_id', 'user_id'),
        db.Index('idx_hired_agent_is_active', 'is_active'),
        db.Index('idx_hired_agent_user_active', 'user_id', 'is_active'),  # Composite index
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    agent_type = db.Column(db.String(50), nullable=False)  # 'market', 'price', 'news', 'digitalization'
    hired_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)

    # Relationship to user
    user = db.relationship('User', backref=db.backref('hired_agents', lazy='dynamic'))


class ContactRequest(db.Model):
    """Model for storing contact form submissions from users"""
    __tablename__ = 'contact_request'
    __table_args__ = (
        db.Index('idx_contact_request_created_at', 'created_at'),
        db.Index('idx_contact_request_status', 'status'),
        db.Index('idx_contact_request_source', 'source'),
    )

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null for landing page submissions
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    company = db.Column(db.String(150), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    message = db.Column(db.Text, nullable=False)
    source = db.Column(db.String(50), nullable=False)  # 'landing_page', 'artifact_panel', 'contact_page'
    status = db.Column(db.String(20), default='pending')  # 'pending', 'contacted', 'resolved'
    selected_experts = db.Column(db.JSON, nullable=True)  # JSON array of selected expert IDs from artifact panel
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    contacted_at = db.Column(db.DateTime, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    notes = db.Column(db.Text, nullable=True)  # Internal notes from sales team

    # Relationship to user (optional)
    user = db.relationship('User', backref=db.backref('contact_requests', lazy='dynamic'))
