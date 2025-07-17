from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta

from app.database import get_db
from app.models.models import User, ClassSchedule, RescheduleRequest, Room, UserType, ScheduleStatus, RescheduleStatus
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/schedule", tags=["Class Scheduling"])

class ClassScheduleCreate(BaseModel):
    student_id: int
    teacher_id: int
    room_id: int
    scheduled_at: datetime
    duration: int = 60
    subject: Optional[str] = None
    notes: Optional[str] = None

class RescheduleRequestCreate(BaseModel):
    schedule_id: int
    requested_datetime: datetime
    reason: Optional[str] = None

class RescheduleResponse(BaseModel):
    request_id: int
    approve: bool
    teacher_response: Optional[str] = None

@router.post("/create")
async def create_class_schedule(
    schedule_data: ClassScheduleCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new class schedule (admin only)"""
    
    if current_user.user_type != UserType.ADMIN:
        raise HTTPException(status_code=403, detail="Only admins can create class schedules")
    
    # Create default room if none exist
    room_result = await db.execute(select(Room).where(Room.id == schedule_data.room_id))
    room = room_result.scalar_one_or_none()
    
    if not room:
        # Create a default room
        default_room = Room(
            name="Main Classroom",
            capacity=1,
            is_available=True,
            equipment={"projector": True, "audio": True}
        )
        db.add(default_room)
        await db.commit()
        await db.refresh(default_room)
        schedule_data.room_id = default_room.id
    
    # Create the schedule
    class_schedule = ClassSchedule(
        student_id=schedule_data.student_id,
        teacher_id=schedule_data.teacher_id,
        room_id=schedule_data.room_id,
        scheduled_at=schedule_data.scheduled_at,
        duration=schedule_data.duration,
        subject=schedule_data.subject,
        notes=schedule_data.notes
    )
    
    db.add(class_schedule)
    await db.commit()
    await db.refresh(class_schedule)
    
    return {
        "message": "Class scheduled successfully",
        "schedule_id": class_schedule.id,
        "schedule": {
            "id": class_schedule.id,
            "student_id": class_schedule.student_id,
            "teacher_id": class_schedule.teacher_id,
            "room_id": class_schedule.room_id,
            "scheduled_at": class_schedule.scheduled_at.isoformat(),
            "duration": class_schedule.duration,
            "subject": class_schedule.subject,
            "status": class_schedule.status.value
        }
    }

@router.get("/my-schedule")
async def get_my_schedule(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's class schedule"""
    
    if current_user.user_type == UserType.STUDENT:
        result = await db.execute(
            select(ClassSchedule)
            .where(
                ClassSchedule.student_id == current_user.id,
                ClassSchedule.status.in_([ScheduleStatus.SCHEDULED, ScheduleStatus.RESCHEDULED])
            )
            .order_by(ClassSchedule.scheduled_at.asc())
        )
    elif current_user.user_type == UserType.TEACHER:
        result = await db.execute(
            select(ClassSchedule)
            .where(
                ClassSchedule.teacher_id == current_user.id,
                ClassSchedule.status.in_([ScheduleStatus.SCHEDULED, ScheduleStatus.RESCHEDULED])
            )
            .order_by(ClassSchedule.scheduled_at.asc())
        )
    else:
        # Admin can see all schedules
        result = await db.execute(
            select(ClassSchedule)
            .order_by(ClassSchedule.scheduled_at.asc())
        )
    
    schedules = result.scalars().all()
    
    return {
        "schedules": [
            {
                "id": schedule.id,
                "scheduled_at": schedule.scheduled_at.isoformat(),
                "duration": schedule.duration,
                "subject": schedule.subject,
                "status": schedule.status.value,
                "student_id": schedule.student_id,
                "teacher_id": schedule.teacher_id,
                "room_id": schedule.room_id,
                "notes": schedule.notes
            }
            for schedule in schedules
        ]
    }

@router.post("/reschedule")
async def request_reschedule(
    request_data: RescheduleRequestCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Request to reschedule a class (student only)"""
    
    if current_user.user_type != UserType.STUDENT:
        raise HTTPException(status_code=403, detail="Only students can request reschedules")
    
    # Get the original schedule
    schedule_result = await db.execute(
        select(ClassSchedule).where(
            ClassSchedule.id == request_data.schedule_id,
            ClassSchedule.student_id == current_user.id,
            ClassSchedule.status == ScheduleStatus.SCHEDULED
        )
    )
    schedule = schedule_result.scalar_one_or_none()
    
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found or cannot be rescheduled")
    
    # Create reschedule request
    reschedule_request = RescheduleRequest(
        student_id=current_user.id,
        original_schedule_id=request_data.schedule_id,
        requested_datetime=request_data.requested_datetime,
        reason=request_data.reason
    )
    
    db.add(reschedule_request)
    await db.commit()
    await db.refresh(reschedule_request)
    
    return {
        "message": "Reschedule request submitted successfully",
        "request_id": reschedule_request.id,
        "status": "pending",
        "requested_datetime": reschedule_request.requested_datetime.isoformat()
    }

@router.get("/reschedule-requests")
async def get_reschedule_requests(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get reschedule requests"""
    
    if current_user.user_type == UserType.STUDENT:
        result = await db.execute(
            select(RescheduleRequest)
            .where(RescheduleRequest.student_id == current_user.id)
            .order_by(RescheduleRequest.created_at.desc())
        )
    elif current_user.user_type == UserType.TEACHER:
        result = await db.execute(
            select(RescheduleRequest)
            .join(ClassSchedule, RescheduleRequest.original_schedule_id == ClassSchedule.id)
            .where(
                ClassSchedule.teacher_id == current_user.id,
                RescheduleRequest.status == RescheduleStatus.PENDING
            )
            .order_by(RescheduleRequest.created_at.desc())
        )
    else:
        # Admin sees all requests
        result = await db.execute(
            select(RescheduleRequest)
            .order_by(RescheduleRequest.created_at.desc())
        )
    
    requests = result.scalars().all()
    
    return {
        "requests": [
            {
                "id": request.id,
                "original_schedule_id": request.original_schedule_id,
                "requested_datetime": request.requested_datetime.isoformat(),
                "reason": request.reason,
                "status": request.status.value,
                "created_at": request.created_at.isoformat(),
                "teacher_response": request.teacher_response,
                "responded_at": request.responded_at.isoformat() if request.responded_at else None
            }
            for request in requests
        ]
    }

@router.post("/reschedule-response")
async def respond_to_reschedule(
    response_data: RescheduleResponse,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Respond to a reschedule request (teacher only)"""
    
    if current_user.user_type != UserType.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can respond to reschedule requests")
    
    # Get the reschedule request
    request_result = await db.execute(
        select(RescheduleRequest, ClassSchedule)
        .join(ClassSchedule, RescheduleRequest.original_schedule_id == ClassSchedule.id)
        .where(
            RescheduleRequest.id == response_data.request_id,
            ClassSchedule.teacher_id == current_user.id,
            RescheduleRequest.status == RescheduleStatus.PENDING
        )
    )
    
    request_data = request_result.first()
    if not request_data:
        raise HTTPException(status_code=404, detail="Reschedule request not found")
    
    reschedule_request, original_schedule = request_data
    
    # Update the request
    reschedule_request.status = RescheduleStatus.APPROVED if response_data.approve else RescheduleStatus.DENIED
    reschedule_request.teacher_response = response_data.teacher_response
    reschedule_request.responded_at = datetime.utcnow()
    
    # If approved, update the original schedule
    if response_data.approve:
        original_schedule.scheduled_at = reschedule_request.requested_datetime
        original_schedule.status = ScheduleStatus.RESCHEDULED
        original_schedule.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": f"Reschedule request {'approved' if response_data.approve else 'denied'}",
        "request_id": reschedule_request.id,
        "status": reschedule_request.status.value,
        "new_datetime": original_schedule.scheduled_at.isoformat() if response_data.approve else None
    }

@router.get("/rooms")
async def get_available_rooms(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available rooms"""
    
    result = await db.execute(
        select(Room).where(Room.is_available == True)
    )
    rooms = result.scalars().all()
    
    # Create default room if none exist
    if not rooms:
        default_room = Room(
            name="Main Classroom",
            capacity=1,
            is_available=True,
            equipment={"projector": True, "audio": True}
        )
        db.add(default_room)
        await db.commit()
        rooms = [default_room]
    
    return {
        "rooms": [
            {
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "equipment": room.equipment
            }
            for room in rooms
        ]
    }
