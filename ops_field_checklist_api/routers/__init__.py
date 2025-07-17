from fastapi import APIRouter
from .res_checklist import checklist_router

PREFIX="/api/v1"
router = APIRouter(prefix=PREFIX)
router.include_router(checklist_router)
