from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class AnswerCode(BaseModel):
    id: int = Field(..., description="Unique identifier for the answer code")
    name: str = Field(..., description="Code name or identifier")
    description: str = Field(..., description="Description of the code")


class Question(BaseModel):
    id: int
    activity_id: int = Field(..., description="ID of the activity this question belongs to")
    name: str = Field(..., description="Question or prompt text")
    answer_type: str = Field(..., description="Type of answer expected (e.g., code, value)")


class Answers(BaseModel):
    question_id: Optional[int] = Field(None, description="ID of the question being answered")
    question: Optional[str] = Field(None, description="Text of the question")
    answer_code_id: Optional[int] = Field(None, description="ID of the selected answer code (if applicable)")
    answer_code: Optional[AnswerCode] = Field(None, description="Details of the selected answer code")
    answer_value: Optional[str] = Field(None, description="Recorded value for the question (if applicable)")


class InspectionActivity(BaseModel):
    id: int = Field(..., description="Unique identifier for the inspection activity")
    name: str = Field(..., description="Name of the inspection activity")
    equipment_name: str = Field(..., description="Name of the equipment related to the activity")
    comment: Optional[str] = Field(None, description="Comment or notes for the activity")
    job_request_state: str = Field(..., description="State of the job request (e.g., pending, confirmed, cancelled)")
    job_status: str = Field(..., description="Status of the job (e.g., open, closed)")
    job_request_raised: bool = Field(..., description="Indicates if a job request has been raised")
    answers: Optional[list[Answers]] = Field(
        description="List of answers provided for the activity"
    )


class ChecklistItem(BaseModel):
    id: int
    name: str = Field(..., description="Name of the checklist item")
    template_id: int = Field(..., description="ID of the checklist template")
    officer_id: int = Field(..., description="ID of the officer responsible for the checklist item")
    state: str = Field(..., description="State of the checklist item (e.g., new, completed, missed)")
    due_date: Optional[datetime] = Field(None, description="Due date for the checklist item")
    inspection_type: str = Field(..., description="Type of inspection (e.g., daily, weekly, monthly)")


class SingleChecklistItem(BaseModel):
    name: str = Field(..., description="Name of the checklist item")
    officer_id: int = Field(..., description="ID of the officer responsible for the checklist item")
    state: str = Field(..., description="State of the checklist item (e.g., new, completed, missed)")
    due_date: Optional[datetime] = Field(None, description="Due date for the checklist item")
    inspection_type: str = Field(..., description="Type of inspection (e.g., daily, weekly, monthly)")
    inspection_activities: list[InspectionActivity] = Field(
        default_factory=list, description="List of activities associated with the checklist item"
    )


class NewQuestion(BaseModel):
    id: int
    activity_id: int = Field(..., description="ID of the activity this question belongs to")
    name: str = Field(..., description="Question or prompt text")
    answer_type: str = Field(..., description="Type of answer expected (e.g., code, value)")
    possible_code_ids: Optional[list[AnswerCode]] = Field(
        description="List of possible answer codes for the question"
    )


class NewInspectionActivity(BaseModel):
    id: int = Field(..., description="Unique identifier for the inspection activity")
    name: str = Field(..., description="Name of the inspection activity")
    equipment_name: str = Field(..., description="Name of the equipment related to the activity")
    questions: list[NewQuestion] = Field(
        description="List of questions associated with the inspection activity"
    )


class NewChecklistItem(BaseModel):
    name: str = Field(..., description="Reference name for the checklist item")
    template_id: int = Field(..., description="ID of the checklist template")
    officer_id: int = Field(..., description="ID of the officer responsible for the checklist item")
    inspection_type: str = Field(..., description="Type of inspection (e.g., daily, weekly, monthly)")
    due_date: Optional[datetime] = Field(None, description="Due date for the checklist item")
    inspection_activities: list[NewInspectionActivity] = Field(
        description="List of activities to be completed by the officer for the checklist item"
    )


class OfficerInspectionAnswer(BaseModel):
    question_id: Optional[int] = Field(None, description="ID of the question being answered")
    answer_code_id: Optional[int] = Field(None, description="ID of the selected answer code (if applicable)")
    answer_value: Optional[str] = Field(None, description="Recorded value for the question (if applicable)")


class Attachment(BaseModel):
    file_name: str = Field(..., description="Name of the file")
    base64_data: str = Field(..., description="Base64-encoded file data")


class OfficerInspectionActivity(BaseModel):
    id: int = Field(..., description="ID of the inspection activity")
    comment: Optional[str] = Field(None, description="Comment or notes for the activity")
    job_request_raised: bool = Field(..., description="Indicates if a job request has been raised by the officer")
    answers: Optional[list[OfficerInspectionAnswer]] = Field(
        description="List of answers provided by the officer for the activity"
    )
    attachments: Optional[list[Attachment]] = Field(
        None, description="List of base64-encoded file data"
    )


class OfficerInspection(BaseModel):
    # inspection_id: int = Field(..., description="ID of the inspection")
    # inspection_reference: str = Field(..., description="Reference number for the inspection")
    date_completed: datetime = Field(..., description="Date when the inspection was completed")
    inspection_activities: list[OfficerInspectionActivity] = Field(
        description="List of activities completed by the officer during the inspection"
    )


class NotificationSummary(BaseModel):
    upcoming_inspections: int = Field(
        default=0, description="Number of upcoming inspections"
    )
    missed_inspections: int = Field(
        default=0, description="Number of missed inspections"
    )
    raised_job_count: int = Field(
        default=0, description="Number of job requests raised from inspections"
    )
    due_today_count: int = Field(
        default=0, description="Number of inspections due today"
    )
