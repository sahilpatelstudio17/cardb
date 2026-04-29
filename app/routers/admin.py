from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import os
import uuid
from pathlib import Path

from app import schemas, crud, models
from app.deps import get_db_dep, get_current_admin

router = APIRouter(prefix="/admin")

# Create media directory for uploads
MEDIA_DIR = Path(__file__).parent.parent.parent / "media" / "cars"
MEDIA_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/cars", response_model=List[schemas.CarOut])
def admin_list_cars(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all cars (admin only)"""
    cars = db.query(models.Car).all()
    return cars


@router.post("/cars", response_model=schemas.CarOut)
def admin_create_car(car_in: schemas.CarCreate, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Create a new car (admin only)"""
    car = models.Car(
        brand=car_in.brand,
        name=car_in.name,
        image=car_in.image,
        category=car_in.category,
        required_plan=car_in.required_plan,
        available=car_in.available
    )
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


@router.post("/cars/upload", response_model=schemas.CarOut)
async def admin_create_car_with_upload(
    brand: str = Form(...),
    name: str = Form(...),
    category: str = Form("Sedan"),
    required_plan: str = Form("basic"),
    available: bool = Form(True),
    image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db_dep),
    admin: models.User = Depends(get_current_admin)
):
    """Create a new car with image upload (admin only)"""
    image_path = None
    
    if image and image.filename:
        # Generate unique filename
        ext = os.path.splitext(image.filename)[1] or ".jpg"
        unique_name = f"{uuid.uuid4().hex}{ext}"
        file_path = MEDIA_DIR / unique_name
        
        # Save file
        content = await image.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        image_path = f"/media/cars/{unique_name}"
    
    car = models.Car(
        brand=brand,
        name=name,
        image=image_path,
        category=category,
        required_plan=required_plan,
        available=available
    )
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


@router.put("/cars/{car_id}", response_model=schemas.CarOut)
def admin_update_car(car_id: int, car_in: schemas.CarCreate, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Update car details (admin only)"""
    car = db.query(models.Car).filter(models.Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    car.brand = car_in.brand
    car.name = car_in.name
    car.image = car_in.image
    car.category = car_in.category if car_in.category else car.category
    car.required_plan = car_in.required_plan if car_in.required_plan else car.required_plan
    car.available = car_in.available
    db.commit()
    db.refresh(car)
    return car


@router.delete("/cars/{car_id}")
def admin_delete_car(car_id: int, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Delete a car (admin only)"""
    car = db.query(models.Car).filter(models.Car.id == car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    
    db.delete(car)
    db.commit()
    return {"detail": "Car deleted successfully"}


@router.get("/subscription-plans", response_model=List[schemas.SubscriptionPlanOut])
def admin_list_plans(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all subscription plans (admin only)"""
    plans = db.query(models.SubscriptionPlan).all()
    return plans


@router.post("/subscription-plans", response_model=schemas.SubscriptionPlanOut)
def admin_create_subscription_plan(plan_in: schemas.SubscriptionPlanCreate, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Create subscription plan (admin only)"""
    plan = models.SubscriptionPlan(
        name=plan_in.name,
        price=plan_in.price,
        duration_months=plan_in.duration_months,
        swap_limit=plan_in.swap_limit,
        tier=plan_in.tier,
        features=plan_in.features,
        max_active_bookings=plan_in.max_active_bookings
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


@router.put("/subscription-plans/{plan_id}", response_model=schemas.SubscriptionPlanOut)
def admin_update_plan(plan_id: int, plan_in: schemas.SubscriptionPlanCreate, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Update subscription plan (admin only)"""
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan.name = plan_in.name
    plan.price = plan_in.price
    plan.duration_months = plan_in.duration_months
    plan.swap_limit = plan_in.swap_limit
    plan.tier = plan_in.tier if plan_in.tier else plan.tier
    plan.features = plan_in.features
    plan.max_active_bookings = plan_in.max_active_bookings
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/subscription-plans/{plan_id}")
def admin_delete_plan(plan_id: int, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Delete a subscription plan (admin only)"""
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    # Check if plan is in use
    active_subs = db.query(models.Subscription).filter(
        models.Subscription.plan_id == plan_id,
        models.Subscription.active == True
    ).count()
    if active_subs > 0:
        raise HTTPException(status_code=400, detail="Cannot delete plan with active subscriptions")
    
    db.delete(plan)
    db.commit()
    return {"detail": "Plan deleted successfully"}


@router.get("/subscriptions")
def admin_list_subscriptions(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all subscriptions (admin only)"""
    subs = db.query(models.Subscription).all()
    result = []
    for sub in subs:
        result.append({
            "id": sub.id,
            "user": {"id": sub.user.id, "email": sub.user.email, "full_name": sub.user.full_name} if sub.user else None,
            "car": {"id": sub.car.id, "brand": sub.car.brand, "name": sub.car.name} if sub.car else None,
            "plan": {"id": sub.plan.id, "name": sub.plan.name, "price": sub.plan.price, "tier": sub.plan.tier} if sub.plan else None,
            "needs_driver": sub.needs_driver,
            "driver_service_details": sub.driver_service_details,
            "start_date": sub.start_date,
            "end_date": sub.end_date,
            "active": sub.active,
            "swaps_count": sub.swaps_count
        })
    return result


# ============== BOOKING MANAGEMENT ==============

@router.get("/bookings")
def admin_list_bookings(status: str = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all booking requests (admin only)"""
    query = db.query(models.Booking)
    if status:
        query = query.filter(models.Booking.status == status)
    
    bookings = query.order_by(models.Booking.created_at.desc()).all()
    result = []
    for booking in bookings:
        car = db.query(models.Car).filter(models.Car.id == booking.car_id).first()
        user = db.query(models.User).filter(models.User.id == booking.user_id).first()
        result.append({
            "id": booking.id,
            "user": {"id": user.id, "email": user.email, "full_name": user.full_name} if user else None,
            "car": {"id": car.id, "brand": car.brand, "name": car.name, "image": car.image, "category": car.category} if car else None,
            "status": booking.status,
            "request_type": booking.request_type,
            "note": booking.note,
            "admin_note": booking.admin_note,
            "created_at": booking.created_at,
            "updated_at": booking.updated_at
        })
    return result


@router.post("/bookings/{booking_id}/approve")
def admin_approve_booking(booking_id: int, approval: schemas.BookingApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Approve a booking request (admin only)"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")
    
    # Check if car is available
    car = db.query(models.Car).filter(models.Car.id == booking.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    
    # Lookup user's active subscription before availability guard.
    user_sub = db.query(models.Subscription).filter(
        models.Subscription.user_id == booking.user_id,
        models.Subscription.active == True
    ).first()

    if not car.available:
        # Allow approval when booking targets the same car already assigned to this user.
        if not user_sub or user_sub.car_id != car.id:
            booking.status = "rejected"
            booking.admin_note = (
                approval.admin_note
                if approval and approval.admin_note
                else "Auto-rejected: car is no longer available"
            )
            db.commit()
            return {"detail": "Booking was auto-rejected because the car is no longer available"}
    
    # Approve booking
    booking.status = "approved"
    if approval and approval.admin_note:
        booking.admin_note = approval.admin_note
    
    # Mark car as unavailable
    car.available = False
    
    # Update user's subscription with this car
    if user_sub:
        # Release previous car if any
        if user_sub.car_id and user_sub.car_id != car.id:
            old_car = db.query(models.Car).filter(models.Car.id == user_sub.car_id).first()
            if old_car:
                old_car.available = True
        user_sub.car_id = car.id
    
    db.commit()
    return {"detail": "Booking approved successfully"}


@router.post("/bookings/{booking_id}/reject")
def admin_reject_booking(booking_id: int, approval: schemas.BookingApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Reject a booking request (admin only)"""
    booking = db.query(models.Booking).filter(models.Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Booking is not pending")
    
    booking.status = "rejected"
    if approval and approval.admin_note:
        booking.admin_note = approval.admin_note
    
    db.commit()
    return {"detail": "Booking rejected"}


# ============== SWAP REQUEST MANAGEMENT ==============

@router.get("/swap-requests")
def admin_list_swap_requests(status: str = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all swap requests (admin only)"""
    query = db.query(models.SwapHistory)
    if status:
        query = query.filter(models.SwapHistory.status == status)
    
    swaps = query.order_by(models.SwapHistory.timestamp.desc()).all()
    result = []
    for swap in swaps:
        from_car = db.query(models.Car).filter(models.Car.id == swap.from_car_id).first()
        to_car = db.query(models.Car).filter(models.Car.id == swap.to_car_id).first()
        sub = db.query(models.Subscription).filter(models.Subscription.id == swap.subscription_id).first()
        result.append({
            "id": swap.id,
            "subscription_id": swap.subscription_id,
            "user": {"id": sub.user.id, "email": sub.user.email, "full_name": sub.user.full_name} if sub and sub.user else None,
            "from_car": {"id": from_car.id, "brand": from_car.brand, "name": from_car.name, "image": from_car.image} if from_car else None,
            "to_car": {"id": to_car.id, "brand": to_car.brand, "name": to_car.name, "image": to_car.image} if to_car else None,
            "status": swap.status,
            "timestamp": swap.timestamp,
            "note": swap.note,
            "admin_note": swap.admin_note
        })
    return result


@router.post("/swap-requests/{swap_id}/approve")
def admin_approve_swap(swap_id: int, approval: schemas.BookingApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Approve a swap request (admin only)"""
    swap = db.query(models.SwapHistory).filter(models.SwapHistory.id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")
    
    if swap.status != "pending":
        raise HTTPException(status_code=400, detail="Swap request is not pending")
    
    # Get subscription
    subscription = db.query(models.Subscription).filter(models.Subscription.id == swap.subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Validate swap limit
    plan = subscription.plan
    if plan and subscription.swaps_count >= plan.swap_limit:
        raise HTTPException(status_code=400, detail=f"User has reached their swap limit ({plan.swap_limit} swaps) for {plan.name} plan")
    
    # Check target car availability
    to_car = db.query(models.Car).filter(models.Car.id == swap.to_car_id).first()
    if not to_car:
        raise HTTPException(status_code=404, detail="Target car not found")
    
    if not to_car.available:
        raise HTTPException(status_code=400, detail="Target car is no longer available")
    
    # Release old car
    if swap.from_car_id:
        old_car = db.query(models.Car).filter(models.Car.id == swap.from_car_id).first()
        if old_car:
            old_car.available = True
    
    # Assign new car
    to_car.available = False
    subscription.car_id = to_car.id
    subscription.swaps_count += 1
    
    # Update swap status
    swap.status = "approved"
    if approval and approval.admin_note:
        swap.admin_note = approval.admin_note
    
    db.commit()
    return {"detail": "Swap approved successfully"}


@router.post("/swap-requests/{swap_id}/reject")
def admin_reject_swap(swap_id: int, approval: schemas.BookingApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Reject a swap request (admin only)"""
    swap = db.query(models.SwapHistory).filter(models.SwapHistory.id == swap_id).first()
    if not swap:
        raise HTTPException(status_code=404, detail="Swap request not found")
    
    if swap.status != "pending":
        raise HTTPException(status_code=400, detail="Swap request is not pending")
    
    swap.status = "rejected"
    if approval and approval.admin_note:
        swap.admin_note = approval.admin_note
    
    db.commit()
    return {"detail": "Swap request rejected"}


# ============== RETURN REQUEST MANAGEMENT ==============

@router.get("/return-requests")
def admin_list_return_requests(status: str = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all return requests (admin only)"""
    query = db.query(models.ReturnRequest)
    if status:
        query = query.filter(models.ReturnRequest.status == status)
    
    return_requests = query.order_by(models.ReturnRequest.created_at.desc()).all()
    result = []
    for ret_req in return_requests:
        sub = db.query(models.Subscription).filter(models.Subscription.id == ret_req.subscription_id).first()
        car = ret_req.car or (sub.car if sub else None)
        result.append({
            "id": ret_req.id,
            "subscription_id": ret_req.subscription_id,
            "user": {"id": ret_req.user.id, "email": ret_req.user.email, "full_name": ret_req.user.full_name} if ret_req.user else None,
            "car": {"id": car.id, "brand": car.brand, "name": car.name, "image": car.image, "category": car.category} if car else None,
            "status": ret_req.status,
            "reason": ret_req.reason,
            "admin_note": ret_req.admin_note,
            "created_at": ret_req.created_at,
            "updated_at": ret_req.updated_at
        })
    return result


@router.post("/return-requests/{return_id}/approve")
def admin_approve_return_request(return_id: int, approval: schemas.ReturnRequestApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Approve a return request (admin only). Remove only the returned car when others remain."""
    return_request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    if return_request.status != "pending":
        raise HTTPException(status_code=400, detail="Return request is not pending")
    
    # Get subscription
    subscription = db.query(models.Subscription).filter(models.Subscription.id == return_request.subscription_id).first()
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    # Release the car being returned
    car_id_to_release = return_request.car_id or subscription.car_id
    if car_id_to_release:
        car = db.query(models.Car).filter(models.Car.id == car_id_to_release).first()
        if car:
            car.available = True

    # Update return request status
    return_request.status = "approved"
    if approval and approval.admin_note:
        return_request.admin_note = approval.admin_note

    booking_note = approval.admin_note if approval and approval.admin_note else "Car returned by user"
    returned_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == return_request.user_id,
        models.Booking.car_id == car_id_to_release,
        models.Booking.status == "approved"
    ).all()
    for booking in returned_bookings:
        booking.status = "returned"
        booking.admin_note = booking_note

    remaining_active_car_ids = crud.get_active_user_car_ids(
        db,
        return_request.user_id,
    )

    if subscription.car_id == car_id_to_release:
        if remaining_active_car_ids:
            subscription.car_id = remaining_active_car_ids[0]
        else:
            subscription.car_id = None
            subscription.active = False
            subscription.end_date = datetime.utcnow()

    db.commit()
    return {"detail": "Return request approved successfully"}


@router.post("/return-requests/{return_id}/reject")
def admin_reject_return_request(return_id: int, approval: schemas.ReturnRequestApproval = None, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Reject a return request (admin only)"""
    return_request = db.query(models.ReturnRequest).filter(models.ReturnRequest.id == return_id).first()
    if not return_request:
        raise HTTPException(status_code=404, detail="Return request not found")
    
    if return_request.status != "pending":
        raise HTTPException(status_code=400, detail="Return request is not pending")
    
    return_request.status = "rejected"
    if approval and approval.admin_note:
        return_request.admin_note = approval.admin_note
    
    db.commit()
    return {"detail": "Return request rejected"}


# ============== CONTACT MESSAGES ==============

@router.get("/contacts", response_model=List[schemas.ContactOut])
def admin_list_contacts(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all contact messages (admin only)"""
    contacts = db.query(models.ContactMessage).order_by(models.ContactMessage.created_at.desc()).all()
    return contacts


@router.post("/contacts/{contact_id}/read")
def admin_mark_contact_read(contact_id: int, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Mark contact message as read (admin only)"""
    contact = db.query(models.ContactMessage).filter(models.ContactMessage.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact message not found")
    
    contact.read = True
    db.commit()
    return {"detail": "Marked as read"}


@router.delete("/contacts/{contact_id}")
def admin_delete_contact(contact_id: int, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Delete contact message (admin only)"""
    contact = db.query(models.ContactMessage).filter(models.ContactMessage.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact message not found")
    
    db.delete(contact)
    db.commit()
    return {"detail": "Contact message deleted"}


@router.get("/users", response_model=List[schemas.UserOut])
def admin_list_users(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """List all users (admin only)"""
    users = db.query(models.User).all()
    return users


@router.delete("/users/{user_id}")
def admin_delete_user(user_id: int, db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Delete a user and all their data (admin only)"""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Cannot delete the admin user themselves
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account")
    
    # Delete all user's subscriptions (cascade will handle related data)
    subscriptions = db.query(models.Subscription).filter(models.Subscription.user_id == user_id).all()
    for sub in subscriptions:
        # Release any cars tied to this subscription
        if sub.car_id:
            car = db.query(models.Car).filter(models.Car.id == sub.car_id).first()
            if car:
                car.available = True
        db.delete(sub)
    
    # Delete all user's bookings
    bookings = db.query(models.Booking).filter(models.Booking.user_id == user_id).all()
    for booking in bookings:
        db.delete(booking)
    
    # Delete user
    db.delete(user)
    db.commit()
    
    return {"detail": f"User {user.email} and all their data deleted successfully"}


@router.get("/stats")
def admin_get_stats(db: Session = Depends(get_db_dep), admin: models.User = Depends(get_current_admin)):
    """Get dashboard statistics (admin only)"""
    total_cars = db.query(models.Car).count()
    available_cars = db.query(models.Car).filter(models.Car.available == True).count()
    total_users = db.query(models.User).filter(models.User.is_admin == False).count()
    active_subscriptions = db.query(models.Subscription).filter(models.Subscription.active == True).count()
    pending_bookings = db.query(models.Booking).filter(models.Booking.status == "pending").count()
    pending_swaps = db.query(models.SwapHistory).filter(models.SwapHistory.status == "pending").count()
    pending_returns = db.query(models.ReturnRequest).filter(models.ReturnRequest.status == "pending").count()
    total_plans = db.query(models.SubscriptionPlan).count()
    unread_contacts = db.query(models.ContactMessage).filter(models.ContactMessage.read == False).count()
    
    return {
        "total_cars": total_cars,
        "available_cars": available_cars,
        "total_users": total_users,
        "active_subscriptions": active_subscriptions,
        "pending_bookings": pending_bookings,
        "pending_swaps": pending_swaps,
        "pending_returns": pending_returns,
        "total_plans": total_plans,
        "unread_contacts": unread_contacts
    }
