# database/models.py
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, asdict, field
from bson import ObjectId

class BaseModel:
    """Base model for all MongoDB documents"""
    
    @classmethod
    @classmethod
    def from_dict(cls, data: dict):
        # Convert string _id to ObjectId if present
        if '_id' in data and isinstance(data['_id'], str):
            try:
                data['_id'] = ObjectId(data['_id'])
            except:
                pass

        # 🔥 FILTER ONLY VALID FIELDS
        allowed_fields = cls.__dataclass_fields__.keys()
        filtered_data = {k: v for k, v in data.items() if k in allowed_fields}

        return cls(**filtered_data)

        # """Create model instance from dictionary"""
        # # Convert string _id to ObjectId if present
        # if '_id' in data and isinstance(data['_id'], str):
        #     try:
        #         data['_id'] = ObjectId(data['_id'])
        #     except:
        #         pass
        # return cls(**data)
    
    def to_dict(self, include_id=True):
        """Convert model to dictionary"""
        data = asdict(self)
        if not include_id and '_id' in data:
            del data['_id']
        # Convert ObjectId to string only if _id exists and is not None
        if '_id' in data and data['_id'] is not None and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        # Remove _id entirely if it's None to avoid duplicate key errors
        if '_id' in data and data['_id'] is None:
            del data['_id']
        return data
    
    def to_json(self):
        """Convert to JSON serializable dict"""
        data = self.to_dict()
        # Handle datetime serialization
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data

@dataclass
class User(BaseModel):
    username: str
    email: str
    password: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    _id: Optional[ObjectId] = None

@dataclass
class HR(BaseModel):
    username: str
    name: str
    email: str
    password: str
    department: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True
    _id: Optional[ObjectId] = None

@dataclass
class Job(BaseModel):
    hr_id: str  # Stored as string (ObjectId converted to string)
    title: str
    department: str
    location: str
    experience: str
    skills: str
    description: str
    hiring_start: datetime
    hiring_end: datetime
    status: str = "Active"
    created_at: datetime = field(default_factory=datetime.now)
    _id: Optional[ObjectId] = None

@dataclass
class Application(BaseModel):
    job_id: str
    user_id: str
    hr_id: str
    applicant_name: str
    email: str
    phone: str
    cover_letter: str
    resume_file: str
    status: str = "Pending"
    date_applied: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class UserActivity(BaseModel):
    user_id: str
    job_id: str
    application_id: str
    status: str
    resume_file: str
    date_applied: datetime = field(default_factory=datetime.now)
    _id: Optional[ObjectId] = None

@dataclass
class Test(BaseModel):
    job_id: str
    title: str
    description: str
    duration_minutes: int
    passing_score: int
    status: str = "Draft"  # Draft, Active, Completed
    created_at: datetime = field(default_factory=datetime.now)
    scheduled_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class Question(BaseModel):
    test_id: str
    question_text: str
    question_type: str  # Multiple Choice, True/False, Short Answer, Essay
    correct_answer: str
    options: List[str] = field(default_factory=list)  # For multiple choice
    points: int = 1
    difficulty: str = "Medium"  # Easy, Medium, Hard
    category: str = "General"
    _id: Optional[ObjectId] = None

@dataclass
class TestSubmission(BaseModel):
    test_id: str
    application_id: str
    candidate_id: str
    answers: Dict[str, Any] = field(default_factory=dict)
    score: int = 0
    total_points: int = 0
    percentage: float = 0.0
    status: str = "In Progress"  # In Progress, Completed, Evaluated
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    evaluated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class Interview(BaseModel):
    application_id: str
    job_id: str
    candidate_id: str
    hr_id: str
    interview_type: str  # Phone, Video, In-person, Technical
    scheduled_datetime: datetime
    duration_minutes: int = 60
    status: str = "Scheduled"  # Scheduled, In Progress, Completed, Cancelled, No Show
    meeting_link: Optional[str] = None
    location: Optional[str] = None
    notes: str = ""
    feedback: str = ""
    rating: Optional[int] = None  # 1-5 scale
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class InterviewFeedback(BaseModel):
    interview_id: str
    interviewer_id: str
    technical_skills: int  # 1-5
    communication_skills: int  # 1-5
    problem_solving: int  # 1-5
    cultural_fit: int  # 1-5
    overall_rating: int  # 1-5
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    comments: str = ""
    recommendation: str = ""  # Hire, Reject, Consider
    created_at: datetime = field(default_factory=datetime.now)
    _id: Optional[ObjectId] = None

@dataclass
class JobOffer(BaseModel):
    application_id: str
    job_id: str
    candidate_id: str
    hr_id: str
    offer_type: str = "Full-time"  # Full-time, Part-time, Contract, Internship
    salary: Optional[float] = None
    start_date: Optional[datetime] = None
    expiry_date: Optional[datetime] = None
    status: str = "Draft"  # Draft, Sent, Accepted, Rejected, Expired
    terms: str = ""
    benefits: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    sent_at: Optional[datetime] = None
    responded_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class ScheduleEvent(BaseModel):
    job_id: str
    event_type: str  # Test, Interview, Offer, Reminder
    title: str
    description: str
    scheduled_datetime: datetime
    status: str = "Scheduled"  # Scheduled, Completed, Cancelled
    participants: List[str] = field(default_factory=list)  # User IDs
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class CandidatePipeline(BaseModel):
    application_id: str
    job_id: str
    candidate_id: str
    current_stage: str = "Applied"  # Applied, Screened, Test, Interview, Offer, Hired, Rejected
    stage_history: List[Dict[str, Any]] = field(default_factory=list)
    next_action: str = ""
    next_action_date: Optional[datetime] = None
    priority: str = "Normal"  # High, Normal, Low
    tags: List[str] = field(default_factory=list)
    notes: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class EmailTemplate(BaseModel):
    name: str
    subject: str
    body: str
    template_type: str  # Test Invitation, Interview Confirmation, Offer Letter, Rejection
    variables: List[str] = field(default_factory=list)  # Template variables like {{candidate_name}}
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    _id: Optional[ObjectId] = None

@dataclass
class EmailLog(BaseModel):
    recipient_email: str
    recipient_name: str
    subject: str
    body: str
    template_id: Optional[str] = None
    status: str = "Sent"  # Sent, Failed, Pending
    sent_at: datetime = field(default_factory=datetime.now)
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    _id: Optional[ObjectId] = None