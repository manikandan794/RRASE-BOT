"""
Aggregates every /api/v1/* route module under one router.
"""
from fastapi import APIRouter

from app.api.v1 import (
    analytics,
    auth,
    chat,
    college_info,
    contacts,
    courses,
    departments,
    documents,
    events,
    facilities,
    faculty,
    faculty_portal,
    faqs,
    feedback,
    health,
    knowledge,
    notices,
    users,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(college_info.router)
api_router.include_router(departments.router)
api_router.include_router(faculty.router)
api_router.include_router(courses.router)
api_router.include_router(faqs.router)
api_router.include_router(notices.router)
api_router.include_router(events.router)
api_router.include_router(facilities.router)
api_router.include_router(contacts.router)
api_router.include_router(documents.router)
api_router.include_router(knowledge.router)
api_router.include_router(knowledge.admin_router)
api_router.include_router(faculty_portal.router)
api_router.include_router(chat.router)
api_router.include_router(feedback.router)
api_router.include_router(analytics.router)
