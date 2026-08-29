"""Pydantic schemas for all structured college-information resources."""
from datetime import datetime

from pydantic import BaseModel, Field


class CollegeInfoIn(BaseModel):
    key: str = Field(min_length=1, max_length=100)
    label: str
    value: str
    source: str | None = None


class CollegeInfoOut(CollegeInfoIn):
    model_config = {"from_attributes": True}


class DepartmentIn(BaseModel):
    name: str
    short_code: str | None = None
    description: str | None = None
    hod_name: str | None = None


class DepartmentOut(DepartmentIn):
    id: str
    model_config = {"from_attributes": True}


class FacultyIn(BaseModel):
    department_id: str | None = None
    full_name: str
    designation: str | None = None
    qualification: str | None = None
    email: str | None = None
    phone: str | None = None
    bio: str | None = None


class FacultyOut(FacultyIn):
    id: str
    model_config = {"from_attributes": True}


class CourseIn(BaseModel):
    department_id: str | None = None
    name: str
    level: str | None = None
    duration_years: int | None = None
    intake: int | None = None
    description: str | None = None


class CourseOut(CourseIn):
    id: str
    model_config = {"from_attributes": True}


class FAQIn(BaseModel):
    # Admin/principal only: sets which department (if any) owns this FAQ.
    # Faculty writes go through /faculty/me/faqs instead, which ignores any
    # department_id the client sends and always uses the server-derived one.
    department_id: str | None = None
    question: str
    answer: str
    category: str | None = None
    is_published: bool = True


class FAQOut(FAQIn):
    id: str
    model_config = {"from_attributes": True}


class NoticeIn(BaseModel):
    department_id: str | None = None
    title: str
    body: str
    is_published: bool = True
    published_at: datetime | None = None
    expires_at: datetime | None = None


class NoticeOut(NoticeIn):
    id: str
    model_config = {"from_attributes": True}


class DepartmentDescriptionUpdate(BaseModel):
    """Faculty may update only their own department's description - name,
    short_code, and hod_name remain admin/principal-only fields."""
    description: str


class EventIn(BaseModel):
    title: str
    description: str | None = None
    location: str | None = None
    starts_at: datetime
    ends_at: datetime | None = None


class EventOut(EventIn):
    id: str
    model_config = {"from_attributes": True}


class FacilityIn(BaseModel):
    name: str
    category: str | None = None
    description: str | None = None


class FacilityOut(FacilityIn):
    id: str
    model_config = {"from_attributes": True}


class ContactIn(BaseModel):
    label: str
    phone: str | None = None
    email: str | None = None
    address: str | None = None


class ContactOut(ContactIn):
    id: str
    model_config = {"from_attributes": True}
