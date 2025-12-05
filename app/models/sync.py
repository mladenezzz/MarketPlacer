from app.models import db
from datetime import datetime


class CollectionLog(db.Model):
    """Модель логов сбора данных"""
    __tablename__ = 'collection_logs'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    marketplace = db.Column(db.String(50), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), nullable=False)
    records_count = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text, nullable=True)
    started_at = db.Column(db.DateTime, nullable=False)
    finished_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('collection_logs', lazy=True))

    __table_args__ = (
        db.Index('idx_collection_logs_token', 'token_id'),
        db.Index('idx_collection_logs_created', 'created_at'),
    )

    def __repr__(self):
        return f'<CollectionLog {self.marketplace}:{self.endpoint} - {self.status}>'


class SyncState(db.Model):
    """Модель состояния синхронизации"""
    __tablename__ = 'sync_states'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    endpoint = db.Column(db.String(100), nullable=False)
    last_sync_date = db.Column(db.DateTime, nullable=True)
    last_successful_sync = db.Column(db.DateTime, nullable=True)
    next_sync_date = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    token = db.relationship('Token', backref=db.backref('sync_states', lazy=True))

    __table_args__ = (
        db.Index('idx_sync_states_token', 'token_id'),
        db.UniqueConstraint('token_id', 'endpoint', name='uix_token_endpoint'),
    )

    def __repr__(self):
        return f'<SyncState {self.endpoint} - {self.last_sync_date}>'


class ManualTask(db.Model):
    """Модель для ручных задач из веб-интерфейса"""
    __tablename__ = 'manual_tasks'

    id = db.Column(db.Integer, primary_key=True)
    token_id = db.Column(db.Integer, db.ForeignKey('tokens.id'), nullable=False)
    task_type = db.Column(db.String(50), nullable=False)  # stocks, goods, sales, orders
    status = db.Column(db.String(20), default='pending')  # pending, processing, completed, failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)
    error_message = db.Column(db.Text, nullable=True)

    token = db.relationship('Token', backref=db.backref('manual_tasks', lazy=True))

    __table_args__ = (
        db.Index('idx_manual_tasks_status', 'status'),
        db.Index('idx_manual_tasks_created', 'created_at'),
    )

    def __repr__(self):
        return f'<ManualTask {self.token_id}:{self.task_type} - {self.status}>'
