from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.encoders import jsonable_encoder

from fastapi.security import APIKeyHeader
from odoo import fields
from odoo.api import Environment
from odoo.addons.fastapi.dependencies import odoo_env
from ..schemas import ChecklistItem, SingleChecklistItem, NewChecklistItem
from ..schemas import OfficerInspection, AnswerCode, NotificationSummary

checklist_router = APIRouter(prefix="", tags=["Checklists"])


@checklist_router.get("/root", response_model=str)
def get_root():
    """
    Returns the root path of the checklist API.
    """
    return "Checklists API Root"


@checklist_router.get("/checklists", response_model=list[ChecklistItem])
def get_officer_checklists(
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a list of checklist names for a given officer ID.
    """
    # single inspection for officer
    single_inspection = env["checklist.inspection"].sudo().search([
        ("state", "in", ["new", "in_progress"]),
    ], limit=1)

    inspections = env["checklist.inspection"].sudo().search([
    ])
    if not inspections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No checklists found for the given officer ID",
        )
    checklist_items = [
        {
            "id": inspection.id,
            "name": inspection.name,
            "template_id": inspection.template_id.id,
            "officer_id": inspection.officer_id.id,
            "state": inspection.state,
            "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
            "inspection_type": inspection.inspection_type,
        }

        for inspection in inspections
    ]
    return checklist_items


@checklist_router.get("/checklists/{checklist_id}", response_model=SingleChecklistItem)
def get_checklist_by_id(
        checklist_id: int,
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a checklist item by its ID.
    """
    inspection = env["checklist.inspection"].sudo().browse(checklist_id)
    if not inspection.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist with ID {checklist_id} not found",
        )
    checklist_item = {
        "id": inspection.id,
        "name": inspection.name,
        "template_id": inspection.template_id.id,
        "officer_id": inspection.officer_id.id,
        "state": inspection.state,
        "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
        "inspection_type": inspection.inspection_type,

    }
    inspection_activities = env["checklist.inspection.activity"].sudo().search([
        ("inspection_id", "=", inspection.id)
    ])
    inspection_activity_list = [
        {
            "id": activity.id,
            "name": activity.activity_id.name,
            "equipment_name": activity.equipment_name if activity.equipment_name else "",
            "comment": activity.comment,
            "job_request_state": activity.job_request_state,
            "job_status": activity.job_status,
            "job_request_raised": activity.job_request_raised,
            "answers": [
                {
                    "question_id": answer.question_id.id,
                    "question": answer.question_id.name,
                    "answer_code": {
                        "id": answer.answer_code_id.id,
                        "name": answer.answer_code_id.name,
                        "description": answer.answer_code_id.description,
                    } if answer.answer_code_id else None,
                    "answer_value": answer.answer_value if answer.answer_value else None,
                }
                for answer in activity.answer_ids
            ],
        }
        for activity in inspection_activities
    ]
    checklist_item["inspection_activities"] = inspection_activity_list
    return checklist_item


@checklist_router.get("/checklists/new/{officer_id}", response_model=NewChecklistItem)
def get_new_checklist(
        officer_id: int,
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a new checklist item for a given officer ID.
    """
    officer = env["res.users"].sudo().browse(officer_id)
    if not officer.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer with ID {officer_id} not found",
        )

    officer_new_inspection = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "in", ["new", "in_progress"]),
    ], limit=1)
    if not officer_new_inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No new checklist found for officer with ID {officer_id}",
        )
    new_checklist = {
        "template_id": officer_new_inspection.template_id.id,
        "officer_id": officer.id,
        "inspection_type": officer_new_inspection.inspection_type,
        "due_date": officer_new_inspection.due_date.isoformat() if officer_new_inspection.due_date else None,
        "inspection_activities": [
            {
                "id": activity.id,
                "name": activity.name,
                "equipment_name": activity.equipment_name if activity.equipment_name else "",
                "questions": [
                    {
                        "id": question.id,
                        "name": question.name,
                        "activity_id": question.activity_id.id,
                        "answer_type": question.answer_type,
                        "possible_code_ids": [
                            {
                                "id": code.id,
                                "name": code.name,
                                "description": code.description
                            } for code in question.possible_code_ids
                        ]
                    }
                    for question in env["checklist.question"].sudo().search([
                        ("activity_id", "=", activity.id)
                    ])
                ]
            }

            for activity in env['checklist.template'].sudo().browse(officer_new_inspection.template_id.id).activity_ids
        ]
    }

    return new_checklist


@checklist_router.post("/checklists/{reference}", response_model=SingleChecklistItem)
def officer_response_to_new_checklist(
        officer_inspection: OfficerInspection,
        reference: str,
        env: Annotated[Environment, Depends(odoo_env)],
):
    inspection = env["checklist.inspection"].sudo().search([
        ("name", "=", reference),
        ("state", "in", ["new", "in_progress"]),
    ], limit=1)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Checklist with reference {reference} not found",
        )
    inspection.write({
        "state": "completed",
        "date_completed": fields.Date.from_string(officer_inspection.date_completed) if officer_inspection.date_completed else False,
    })
    for activity in officer_inspection.inspection_activities:
        inspection_activity = env["checklist.inspection.activity"].sudo().create({
            "inspection_id": inspection.id,
            "activity_id": activity.id,
            "job_request_raised": activity.job_request_raised,
            "comment": activity.comment,
        })
        for attachment in activity.attachments:
            attachment_data = {
                'name': attachment.file_name,
                'datas': attachment.base64_data,
                'res_model': 'checklist.inspection.activity',
                'res_id': inspection_activity.id,
                'type': 'binary',
            }
            attachment_record = env['ir.attachment'].sudo().create(attachment_data)
            inspection_activity.attachment_ids = [(4, attachment_record.id)]

        for question in activity.answers:
            answer_values = {
                "inspection_activity_id": inspection_activity.id,
                "question_id": question.question_id,
                "answer_code_id": question.answer_code_id if question.answer_code_id else False,
                "answer_value": question.answer_value if question.answer_value else False,
            }
            env["checklist.answer"].sudo().create(answer_values)

        updated_inspection = env["checklist.inspection"].sudo().browse(inspection.id)
        return {
            "id": updated_inspection.id,
            "name": updated_inspection.name,
            "template_id": updated_inspection.template_id.id,
            "officer_id": updated_inspection.officer_id.id,
            "state": updated_inspection.state,
            "due_date": updated_inspection.due_date.isoformat() if updated_inspection.due_date else None,
            "inspection_type": updated_inspection.inspection_type,
            "inspection_activities": [
                {
                    "id": activity.id,
                    "name": activity.activity_id.name,
                    "equipment_name": activity.equipment_name if activity.equipment_name else "",
                    "comment": activity.comment,
                    "job_request_state": activity.job_request_state,
                    "job_status": activity.job_status,
                    "job_request_raised": activity.job_request_raised,
                    "answers": [
                        {
                            "question_id": answer.question_id.id,
                            "question": answer.question_id.name,
                            "answer_code": {
                                "id": answer.answer_code_id.id,
                                "name": answer.answer_code_id.name,
                                "description": answer.answer_code_id.description
                            } if answer.answer_code_id else None,
                            "answer_value": answer.answer_value if answer.answer_value else None,
                        }
                        for answer in activity.answer_ids
                    ],
                }
                for activity in inspection_activity
            ]
        }


@checklist_router.get("/checklists/officer/{officer_id}", response_model=list[SingleChecklistItem])
def get_checklists_by_officer_id(
        officer_id: int,
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a list of checklist items for a given officer ID.
    """
    officer = env["res.users"].sudo().browse(officer_id)
    if not officer.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer with ID {officer_id} not found",
        )

    inspections = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "in", ["missed", "reviewed", "completed"]),
    ])
    if not inspections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No checklists found for officer with ID {officer_id}",
        )

    checklist_items = [
        {
            "id": inspection.id,
            "name": inspection.name,
            "template_id": inspection.template_id.id,
            "officer_id": inspection.officer_id.id,
            "state": inspection.state,
            "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
            "inspection_type": inspection.inspection_type,
            "inspection_activities": [
                {
                    "id": activity.id,
                    "name": activity.activity_id.name,
                    "equipment_name": activity.equipment_name if activity.equipment_name else "",
                    "comment": activity.comment,
                    "job_request_state": activity.job_request_state,
                    "job_status": activity.job_status,
                    "job_request_raised": activity.job_request_raised,
                    "answers": [
                        {
                            "question_id": answer.question_id.id,
                            "question": answer.question_id.name,
                            "answer_code": {
                                "id": answer.answer_code_id.id,
                                "name": answer.answer_code_id.name,
                                "description": answer.answer_code_id.description
                            } if answer.answer_code_id else None,
                            "answer_value": answer.answer_value if answer.answer_value else None,
                        }
                        for answer in activity.answer_ids
                    ],
                }
                for activity in inspection.inspection_activity_ids
            ],
        }
        for inspection in inspections
    ]
    return checklist_items



@checklist_router.get("/checklists/faults/{officer_id}", response_model=list[SingleChecklistItem])
def get_officer_fault_raised_checklists(
        officer_id: int,
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a list of checklist items for a given officer ID where a fault has been raised.
    """
    officer = env["res.users"].sudo().browse(officer_id)
    if not officer.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer with ID {officer_id} not found",
        )

    inspections = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "in", ["missed", "reviewed", "completed"]),
        ("inspection_activity_ids.job_request_raised", "=", True),
    ])
    if not inspections:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No checklists with faults found for officer with ID {officer_id}",
        )

    checklist_items = [
        {
            "id": inspection.id,
            "name": inspection.name,
            "template_id": inspection.template_id.id,
            "officer_id": inspection.officer_id.id,
            "state": inspection.state,
            "due_date": inspection.due_date.isoformat() if inspection.due_date else None,
            "inspection_type": inspection.inspection_type,
            "inspection_activities": [
                {
                    "id": activity.id,
                    "name": activity.activity_id.name,
                    "equipment_name": activity.equipment_name if activity.equipment_name else "",
                    "comment": activity.comment,
                    "job_request_state": activity.job_request_state,
                    "job_status": activity.job_status,
                    "job_request_raised": activity.job_request_raised,
                    "answers": [
                        {
                            "question_id": answer.question_id.id,
                            "question": answer.question_id.name,
                            "answer_code": {
                                "id": answer.answer_code_id.id,
                                "name": answer.answer_code_id.name,
                                "description": answer.answer_code_id.description
                            } if answer.answer_code_id else None,
                            "answer_value": answer.answer_value if answer.answer_value else None,
                        }
                        for answer in activity.answer_ids
                    ],
                }
                for activity in inspection.inspection_activity_ids
            ],
        }
        for inspection in inspections
    ]
    return checklist_items



@checklist_router.get("/checklists/answer_codes/answers", response_model=list[AnswerCode])
def get_answer_codes(
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a list of answer codes.
    """
    answer_codes = env["checklist.answer.code"].sudo().search([])
    if not answer_codes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No answer codes found",
        )
    return [
        {
            "id": code.id,
            "name": code.name,
            "description": code.description,
        }
        for code in answer_codes
    ]



@checklist_router.get("/checklists/notification/summary/{officer_id}", response_model=NotificationSummary)
def get_officer_notification_summary(
        officer_id: int,
        env: Annotated[Environment, Depends(odoo_env)],
):
    """
    Returns a summary of notifications for a given officer ID.
    """
    officer = env["res.users"].sudo().browse(officer_id)
    if not officer.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Officer with ID {officer_id} not found",
        )
    today_str = fields.Date.today().isoformat()

    up_coming_inspections = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "in", ["new", "in_progress"]),
        ("due_date", "=", today_str),
    ])
    missed_inspections = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "=", "missed"),
    ])
    raised_job_count = env["checklist.inspection.activity"].sudo().search_count([
        ("inspection_id.officer_id", "=", officer.id),
        ("job_request_raised", "=", True),
    ])
    due_today_count = env["checklist.inspection"].sudo().search_count([
        ("officer_id", "=", officer.id),
        ("state", "in", ["new", "in_progress"]),
        ("due_date", "=", today_str),
    ])

    assigned_inspections = env["checklist.inspection"].sudo().search([
        ("officer_id", "=", officer.id),
        ("state", "in", ["new", "in_progress"]),
    ])

    return {
        "up_coming_inspections": len(up_coming_inspections),
        "missed_inspections": len(missed_inspections),
        "raised_job_count": raised_job_count,
        "due_today_count": due_today_count,
    }



