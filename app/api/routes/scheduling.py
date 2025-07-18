from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, validator
from datetime import datetime, timedelta, time
from typing import List, Optional, Dict, Any
import pytz
from enum import Enum

from app.database import get_db
from app.models.models import User, Class, Room, TeacherAvailability, ClassStatus, UserRole
from app.api.auth.auth import get_current_active_user

router = APIRouter(prefix="/api/scheduling", tags=["Class Scheduling"])

class TimeSlot(BaseModel):
    start_time: datetime
    end_time: datetime
    timezone: str = "UTC"

class ClassRequest(BaseModel):
    teacher_id: int
    room_id: int
    scheduled_start: datetime
    scheduled_end: datetime
    subject: str
    language: str = "english"
    class_type: str = "individual"
    lesson_plan: Optional[str] = None

class RescheduleRequest(BaseModel):
    class_id: int
    new_start: datetime
    new_end: datetime
    reason: Optional[str] = None

class AvailabilitySlot(BaseModel):
    day_of_week: int  # 0=Monday, 6=Sunday
    start_time: str   # "09:00"
    end_time: str     # "17:00"
    timezone: str = "UTC"

class TeacherAvailabilityRequest(BaseModel):
    availability_slots: List[AvailabilitySlot]
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None

class SchedulingService:
    """Service for managing class scheduling and availability"""
    
    @staticmethod
    async def check_teacher_availability(
        db: AsyncSession,
        teacher_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if teacher is available for the given time slot"""
        
        # Check existing classes
        existing_classes = await db.execute(
            select(Class).where(
                and_(
                    Class.teacher_id == teacher_id,
                    Class.status.in_([ClassStatus.SCHEDULED]),
                    or_(
                        and_(Class.scheduled_start <= start_time, Class.scheduled_end > start_time),
                        and_(Class.scheduled_start < end_time, Class.scheduled_end >= end_time),
                        and_(Class.scheduled_start >= start_time, Class.scheduled_end <= end_time)
                    )
                )
            )
        )
        
        if existing_classes.first():
            return False
        
        # Check teacher availability schedule
        day_of_week = start_time.weekday()  # 0=Monday
        start_time_str = start_time.strftime("%H:%M")
        end_time_str = end_time.strftime("%H:%M")
        
        availability = await db.execute(
            select(TeacherAvailability).where(
                and_(
                    TeacherAvailability.teacher_id == teacher_id,
                    TeacherAvailability.day_of_week == day_of_week,
                    TeacherAvailability.is_available == True,
                    TeacherAvailability.start_time <= start_time_str,
                    TeacherAvailability.end_time >= end_time_str
                )
            )
        )
        
        return availability.first() is not None
    
    @staticmethod
    async def check_room_availability(
        db: AsyncSession,
        room_id: int,
        start_time: datetime,
        end_time: datetime
    ) -> bool:
        """Check if room is available for the given time slot"""
        
        existing_classes = await db.execute(
            select(Class).where(
                and_(
                    Class.room_id == room_id,
                    Class.status.in_([ClassStatus.SCHEDULED]),
                    or_(
                        and_(Class.scheduled_start <= start_time, Class.scheduled_end > start_time),
                        and_(Class.scheduled_start < end_time, Class.scheduled_end >= end_time),
                        and_(Class.scheduled_start >= start_time, Class.scheduled_end <= end_time)
                    )
                )
            )
        )
        
        return existing_classes.first() is None
    
    @staticmethod
    async def find_available_slots(
        db: AsyncSession,
        teacher_id: int,
        duration_minutes: int = 60,
        days_ahead: int = 14
    ) -> List[Dict[str, Any]]:
        """Find available time slots for a teacher"""
        
        available_slots = []
        start_date = datetime.utcnow().date()
        
        # Get teacher availability
        teacher_availability = await db.execute(
            select(TeacherAvailability).where(
                and_(
                    TeacherAvailability.teacher_id == teacher_id,
                    TeacherAvailability.is_available == True
                )
            )
        )
        
        availability_rules = teacher_availability.scalars().all()
        
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            day_of_week = current_date.weekday()
            
            # Find availability rules for this day
            day_rules = [rule for rule in availability_rules if rule.day_of_week == day_of_week]
            
            for rule in day_rules:
                # Generate time slots
                start_time = datetime.combine(current_date, 
                    datetime.strptime(rule.start_time, "%H:%M").time())
                end_time = datetime.combine(current_date,
                    datetime.strptime(rule.end_time, "%H:%M").time())
                
                current_slot = start_time
                while current_slot + timedelta(minutes=duration_minutes) <= end_time:
                    slot_end = current_slot + timedelta(minutes=duration_minutes)
                    
                    # Check if this slot is available
                    if await SchedulingService.check_teacher_availability(
                        db, teacher_id, current_slot, slot_end
                    ):
                        available_slots.append({
                            "start_time": current_slot.isoformat(),
                            "end_time": slot_end.isoformat(),
                            "duration_minutes": duration_minutes,
                            "day_of_week": day_of_week
                        })
                    
                    current_slot += timedelta(minutes=30)  # 30-minute intervals
        
        return available_slots
    
    @staticmethod
    async def schedule_class(
        db: AsyncSession,
        class_request: ClassRequest,
        student_id: int
    ) -> Class:
        """Schedule a new class"""
        
        # Validate teacher availability
        if not await SchedulingService.check_teacher_availability(
            db, class_request.teacher_id, 
            class_request.scheduled_start, class_request.scheduled_end
        ):
            raise HTTPException(
                status_code=400,
                detail="Teacher is not available at the requested time"
            )
        
        # Validate room availability
        if not await SchedulingService.check_room_availability(
            db, class_request.room_id,
            class_request.scheduled_start, class_request.scheduled_end
        ):
            raise HTTPException(
                status_code=400,
                detail="Room is not available at the requested time"
            )
        
        # Create the class
        new_class = Class(
            teacher_id=class_request.teacher_id,
            student_id=student_id,
            room_id=class_request.room_id,
            scheduled_start=class_request.scheduled_start,
            scheduled_end=class_request.scheduled_end,
            subject=class_request.subject,
            language=class_request.language,
            class_type=class_request.class_type,
            lesson_plan=class_request.lesson_plan,
            status=ClassStatus.SCHEDULED
        )
        
        db.add(new_class)
        await db.commit()
        await db.refresh(new_class)
        
        return new_class

# === API Endpoints ===

@router.post("/classes/schedule")
async def schedule_class(
    class_request: ClassRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Schedule a new class (students and admins)"""
    
    if current_user.role not in [UserRole.STUDENT, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only students and admins can schedule classes"
        )
    
    student_id = current_user.id if current_user.role == UserRole.STUDENT else class_request.student_id
    
    try:
        new_class = await SchedulingService.schedule_class(db, class_request, student_id)
        
        return {
            "message": "Class scheduled successfully",
            "class_id": new_class.id,
            "scheduled_start": new_class.scheduled_start.isoformat(),
            "scheduled_end": new_class.scheduled_end.isoformat(),
            "teacher_id": new_class.teacher_id,
            "room_id": new_class.room_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to schedule class: {str(e)}")

@router.get("/teachers/{teacher_id}/availability")
async def get_teacher_availability(
    teacher_id: int,
    days_ahead: int = 14,
    duration_minutes: int = 60,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available time slots for a teacher"""
    
    # Verify teacher exists
    teacher_result = await db.execute(
        select(User).where(
            and_(User.id == teacher_id, User.role == UserRole.TEACHER, User.is_active == True)
        )
    )
    teacher = teacher_result.scalar_one_or_none()
    
    if not teacher:
        raise HTTPException(status_code=404, detail="Teacher not found")
    
    available_slots = await SchedulingService.find_available_slots(
        db, teacher_id, duration_minutes, days_ahead
    )
    
    return {
        "teacher_id": teacher_id,
        "teacher_name": teacher.full_name,
        "available_slots": available_slots,
        "total_slots": len(available_slots),
        "duration_minutes": duration_minutes,
        "days_ahead": days_ahead
    }

@router.post("/teachers/availability")
async def set_teacher_availability(
    availability_request: TeacherAvailabilityRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Set teacher availability (teachers and admins only)"""
    
    if current_user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=403,
            detail="Only teachers and admins can set availability"
        )
    
    teacher_id = current_user.id if current_user.role == UserRole.TEACHER else None
    
    if current_user.role == UserRole.ADMIN and not teacher_id:
        raise HTTPException(
            status_code=400,
            detail="Admin must specify teacher_id"
        )
    
    try:
        # Clear existing availability
        await db.execute(
            select(TeacherAvailability).where(TeacherAvailability.teacher_id == teacher_id)
        )
        
        # Add new availability slots
        new_slots = []
        for slot in availability_request.availability_slots:
            availability = TeacherAvailability(
                teacher_id=teacher_id,
                day_of_week=slot.day_of_week,
                start_time=slot.start_time,
                end_time=slot.end_time,
                timezone=slot.timezone,
                is_available=True,
                valid_from=availability_request.valid_from,
                valid_until=availability_request.valid_until
            )
            new_slots.append(availability)
            db.add(availability)
        
        await db.commit()
        
        return {
            "message": "Availability updated successfully",
            "teacher_id": teacher_id,
            "slots_added": len(new_slots)
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update availability: {str(e)}")

@router.post("/classes/{class_id}/reschedule")
async def reschedule_class(
    class_id: int,
    reschedule_request: RescheduleRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Reschedule an existing class"""
    
    # Get the class
    class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    existing_class = class_result.scalar_one_or_none()
    
    if not existing_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check permissions
    if current_user.role == UserRole.STUDENT and existing_class.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only reschedule your own classes")
    elif current_user.role == UserRole.TEACHER and existing_class.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only reschedule your own classes")
    
    # Check if class can be rescheduled (not too close to start time)
    time_until_class = existing_class.scheduled_start - datetime.utcnow()
    if time_until_class < timedelta(hours=24):
        raise HTTPException(
            status_code=400,
            detail="Cannot reschedule classes less than 24 hours before start time"
        )
    
    # Check availability for new time
    if not await SchedulingService.check_teacher_availability(
        db, existing_class.teacher_id,
        reschedule_request.new_start, reschedule_request.new_end
    ):
        raise HTTPException(
            status_code=400,
            detail="Teacher is not available at the new requested time"
        )
    
    if not await SchedulingService.check_room_availability(
        db, existing_class.room_id,
        reschedule_request.new_start, reschedule_request.new_end
    ):
        raise HTTPException(
            status_code=400,
            detail="Room is not available at the new requested time"
        )
    
    # Update the class
    existing_class.scheduled_start = reschedule_request.new_start
    existing_class.scheduled_end = reschedule_request.new_end
    existing_class.status = ClassStatus.RESCHEDULED
    existing_class.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Class rescheduled successfully",
        "class_id": class_id,
        "new_start": reschedule_request.new_start.isoformat(),
        "new_end": reschedule_request.new_end.isoformat(),
        "reason": reschedule_request.reason
    }

@router.post("/classes/{class_id}/cancel")
async def cancel_class(
    class_id: int,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Cancel a scheduled class"""
    
    # Get the class
    class_result = await db.execute(
        select(Class).where(Class.id == class_id)
    )
    existing_class = class_result.scalar_one_or_none()
    
    if not existing_class:
        raise HTTPException(status_code=404, detail="Class not found")
    
    # Check permissions
    if current_user.role == UserRole.STUDENT and existing_class.student_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only cancel your own classes")
    elif current_user.role == UserRole.TEACHER and existing_class.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="Can only cancel your own classes")
    
    # Check cancellation policy (e.g., 24 hours notice)
    time_until_class = existing_class.scheduled_start - datetime.utcnow()
    if time_until_class < timedelta(hours=24) and current_user.role == UserRole.STUDENT:
        raise HTTPException(
            status_code=400,
            detail="Students cannot cancel classes less than 24 hours before start time"
        )
    
    # Cancel the class
    existing_class.status = ClassStatus.CANCELLED
    existing_class.teacher_notes = f"Cancelled by {current_user.role.value}: {reason}" if reason else f"Cancelled by {current_user.role.value}"
    existing_class.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Class cancelled successfully",
        "class_id": class_id,
        "cancelled_by": current_user.role.value,
        "reason": reason
    }

@router.get("/classes/my-schedule")
async def get_my_schedule(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's class schedule"""
    
    if not start_date:
        start_date = datetime.utcnow()
    if not end_date:
        end_date = start_date + timedelta(days=30)
    
    # Build query based on user role
    if current_user.role == UserRole.STUDENT:
        query = select(Class).where(
            and_(
                Class.student_id == current_user.id,
                Class.scheduled_start >= start_date,
                Class.scheduled_start <= end_date
            )
        ).options(
            selectinload(Class.teacher),
            selectinload(Class.room)
        ).order_by(Class.scheduled_start)
    
    elif current_user.role == UserRole.TEACHER:
        query = select(Class).where(
            and_(
                Class.teacher_id == current_user.id,
                Class.scheduled_start >= start_date,
                Class.scheduled_start <= end_date
            )
        ).options(
            selectinload(Class.student),
            selectinload(Class.room)
        ).order_by(Class.scheduled_start)
    
    else:  # Admin
        query = select(Class).where(
            and_(
                Class.scheduled_start >= start_date,
                Class.scheduled_start <= end_date
            )
        ).options(
            selectinload(Class.teacher),
            selectinload(Class.student),
            selectinload(Class.room)
        ).order_by(Class.scheduled_start)
    
    result = await db.execute(query)
    classes = result.scalars().all()
    
    schedule = []
    for cls in classes:
        class_info = {
            "class_id": cls.id,
            "subject": cls.subject,
            "language": cls.language,
            "scheduled_start": cls.scheduled_start.isoformat(),
            "scheduled_end": cls.scheduled_end.isoformat(),
            "status": cls.status.value,
            "room": {
                "id": cls.room.id,
                "name": cls.room.name,
                "type": cls.room.room_type
            } if cls.room else None
        }
        
        if current_user.role == UserRole.STUDENT:
            class_info["teacher"] = {
                "id": cls.teacher.id,
                "name": cls.teacher.full_name,
                "specializations": cls.teacher.specializations
            } if cls.teacher else None
        elif current_user.role == UserRole.TEACHER:
            class_info["student"] = {
                "id": cls.student.id,
                "name": cls.student.full_name,
                "level": cls.student.current_level
            } if cls.student else None
        else:  # Admin
            class_info["teacher"] = {
                "id": cls.teacher.id,
                "name": cls.teacher.full_name
            } if cls.teacher else None
            class_info["student"] = {
                "id": cls.student.id,
                "name": cls.student.full_name
            } if cls.student else None
        
        schedule.append(class_info)
    
    return {
        "schedule": schedule,
        "total_classes": len(schedule),
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        }
    }

@router.get("/rooms")
async def get_available_rooms(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available rooms, optionally filtered by time"""
    
    query = select(Room).where(Room.is_active == True)
    
    if start_time and end_time:
        # Find rooms not booked during this time
        booked_rooms = await db.execute(
            select(Class.room_id).where(
                and_(
                    Class.status == ClassStatus.SCHEDULED,
                    or_(
                        and_(Class.scheduled_start <= start_time, Class.scheduled_end > start_time),
                        and_(Class.scheduled_start < end_time, Class.scheduled_end >= end_time),
                        and_(Class.scheduled_start >= start_time, Class.scheduled_end <= end_time)
                    )
                )
            )
        )
        booked_room_ids = [row[0] for row in booked_rooms.fetchall()]
        
        if booked_room_ids:
            query = query.where(Room.id.notin_(booked_room_ids))
    
    result = await db.execute(query)
    rooms = result.scalars().all()
    
    return {
        "rooms": [
            {
                "id": room.id,
                "name": room.name,
                "capacity": room.capacity,
                "type": room.room_type,
                "equipment": room.equipment
            }
            for room in rooms
        ],
        "total_available": len(rooms),
        "time_filter": {
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None
        }
    }

@router.get("/teachers")
async def get_available_teachers(
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    subject: Optional[str] = None,
    language: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available teachers, optionally filtered by time and subject"""
    
    query = select(User).where(
        and_(
            User.role == UserRole.TEACHER,
            User.is_active == True
        )
    )
    
    result = await db.execute(query)
    teachers = result.scalars().all()
    
    available_teachers = []
    for teacher in teachers:
        # Filter by specialization if requested
        if subject and teacher.specializations:
            if subject.lower() not in [spec.lower() for spec in teacher.specializations]:
                continue
        
        # Check availability if time specified
        if start_time and end_time:
            is_available = await SchedulingService.check_teacher_availability(
                db, teacher.id, start_time, end_time
            )
            if not is_available:
                continue
        
        available_teachers.append({
            "id": teacher.id,
            "name": teacher.full_name,
            "specializations": teacher.specializations or [],
            "hourly_rate": teacher.hourly_rate,
            "rating": 4.5  # Placeholder - implement rating system
        })
    
    return {
        "teachers": available_teachers,
        "total_available": len(available_teachers),
        "filters": {
            "start_time": start_time.isoformat() if start_time else None,
            "end_time": end_time.isoformat() if end_time else None,
            "subject": subject,
            "language": language
        }
    }