from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app import schemas, crud, models
from app.deps import get_db_dep, get_current_user

router = APIRouter()


@router.get("/subscription-plans", response_model=List[schemas.SubscriptionPlanOut])
def get_subscription_plans(db: Session = Depends(get_db_dep)):
    """Get all available subscription plans"""
    plans = db.query(models.SubscriptionPlan).all()
    return plans


@router.post("/subscribe", response_model=schemas.SubscriptionOut)
def subscribe(req: schemas.SubscribeRequest, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Subscribe user to a plan and car"""
    try:
        sub = crud.create_subscription(
            db,
            current_user,
            req.car_id,
            req.plan_id,
            req.needs_driver,
            req.driver_service_details,
        )
        return sub
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/my-subscription", response_model=schemas.SubscriptionOut)
def get_user_subscription(db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Get current user's active subscription"""
    subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.active == True
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="No active subscription found")
    
    return subscription


# Booking endpoints
@router.post("/bookings", response_model=schemas.BookingOut)
def create_booking(req: schemas.BookingCreate, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Create a booking request for a car"""
    # Check if user has an active subscription
    subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.active == True
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=400, detail="You need an active subscription to book a car")
    
    # Check if car exists and is available
    car = db.query(models.Car).filter(models.Car.id == req.car_id).first()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    
    # Check if car matches subscription plan tier
    plan = subscription.plan
    plan_tier_order = {"basic": 1, "premium": 2, "luxury": 3}
    user_tier = plan_tier_order.get(plan.tier.lower() if plan.tier else "basic", 1)
    car_required = plan_tier_order.get(car.required_plan.lower() if car.required_plan else "basic", 1)
    
    if user_tier < car_required:
        raise HTTPException(status_code=400, detail=f"This car requires a {car.required_plan} plan or higher")

    # Enforce plan booking capacity in a single active window.
    max_bookings = plan.max_active_bookings or 1
    
    # Count both pending AND approved bookings
    active_bookings_count = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.status.in_(["pending", "approved"])
    ).count()

    if active_bookings_count >= max_bookings:
        remaining = max_bookings - active_bookings_count
        raise HTTPException(
            status_code=400,
            detail=f"Your {plan.name} plan allows only {max_bookings} active booking(s). You have {active_bookings_count} active. Remaining: {remaining}. Please swap a car instead of booking new ones."
        )
    
    # Check for existing pending booking
    existing = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.car_id == req.car_id,
        models.Booking.status == "pending"
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending booking for this car")
    
    # Create booking
    booking = models.Booking(
        user_id=current_user.id,
        car_id=req.car_id,
        status="pending",
        request_type="booking",
        note=req.note
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


@router.get("/my-bookings", response_model=List[schemas.BookingOut])
def get_user_bookings(db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Get current user's booking requests"""
    bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id
    ).order_by(models.Booking.created_at.desc()).all()
    return bookings


@router.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Cancel a pending booking request"""
    booking = db.query(models.Booking).filter(
        models.Booking.id == booking_id,
        models.Booking.user_id == current_user.id
    ).first()
    
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    if booking.status != "pending":
        raise HTTPException(status_code=400, detail="Can only cancel pending bookings")
    
    db.delete(booking)
    db.commit()
    return {"detail": "Booking cancelled"}


# Swap endpoints
@router.post("/swap-request", response_model=schemas.SwapOut)
def create_swap_request(req: schemas.SwapRequest, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Create a swap request (requires admin approval)"""
    subscription = db.query(models.Subscription).filter(
        models.Subscription.id == req.subscription_id,
        models.Subscription.user_id == current_user.id
    ).first()
    
    if not subscription:
        raise HTTPException(status_code=404, detail="Subscription not found")
    
    if not subscription.active:
        raise HTTPException(status_code=400, detail="Subscription is not active")
    
    # Check swap limit
    plan = subscription.plan
    if plan and subscription.swaps_count >= plan.swap_limit:
        raise HTTPException(status_code=400, detail="Swap limit reached for your plan")
    
    # Check if target car exists and is available
    to_car = db.query(models.Car).filter(models.Car.id == req.to_car_id).first()
    if not to_car:
        raise HTTPException(status_code=404, detail="Target car not found")
    
    if not to_car.available:
        raise HTTPException(status_code=400, detail="Target car is not available")
    
    # Check plan tier compatibility
    plan_tier_order = {"basic": 1, "premium": 2, "luxury": 3}
    user_tier = plan_tier_order.get(plan.tier.lower() if plan and plan.tier else "basic", 1)
    car_required = plan_tier_order.get(to_car.required_plan.lower() if to_car.required_plan else "basic", 1)
    
    if user_tier < car_required:
        raise HTTPException(status_code=400, detail=f"This car requires a {to_car.required_plan} plan or higher")
    
    # Check for existing pending swap
    existing = db.query(models.SwapHistory).filter(
        models.SwapHistory.subscription_id == req.subscription_id,
        models.SwapHistory.status == "pending"
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="You already have a pending swap request")
    
    requested_from_car_id = req.from_car_id if req.from_car_id else subscription.car_id

    if not requested_from_car_id:
        raise HTTPException(status_code=400, detail="No source car selected for swap")

    if requested_from_car_id == req.to_car_id:
        raise HTTPException(status_code=400, detail="Source and target cars cannot be the same")

    # Build active swappable cars for this user.
    active_car_ids = set()
    if subscription.car_id:
        active_car_ids.add(subscription.car_id)

    approved_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == current_user.id,
        models.Booking.status == "approved"
    ).all()
    for booking in approved_bookings:
        if booking.car_id:
            active_car_ids.add(booking.car_id)

    user_subscriptions = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id
    ).all()
    user_subscription_ids = [s.id for s in user_subscriptions]

    if user_subscription_ids:
        approved_swaps = db.query(models.SwapHistory).filter(
            models.SwapHistory.subscription_id.in_(user_subscription_ids),
            models.SwapHistory.status == "approved"
        ).all()

        swapped_from_ids = set()
        for swap_item in approved_swaps:
            if swap_item.to_car_id:
                active_car_ids.add(swap_item.to_car_id)
            if swap_item.from_car_id:
                swapped_from_ids.add(swap_item.from_car_id)

        active_car_ids = active_car_ids - swapped_from_ids

    if requested_from_car_id not in active_car_ids:
        raise HTTPException(status_code=400, detail="Selected return car is not active for your account")

    # Create swap request
    from_car_id = requested_from_car_id
    swap = models.SwapHistory(
        subscription_id=subscription.id,
        from_car_id=from_car_id,
        to_car_id=req.to_car_id,
        status="pending",
        note=req.note
    )
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap


@router.post("/swap", response_model=schemas.SwapOut)
def swap(req: schemas.SwapRequest, db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Swap car in subscription (legacy - direct swap)"""
    try:
        swap = crud.swap_subscription(db, current_user, req.subscription_id, req.to_car_id, req.note)
        return swap
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/swap-history", response_model=List[schemas.SwapOut])
def get_swap_history(db: Session = Depends(get_db_dep), current_user: models.User = Depends(get_current_user)):
    """Get swap history for current user"""
    subscriptions = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id
    ).all()
    
    subscription_ids = [s.id for s in subscriptions]
    
    swaps = db.query(models.SwapHistory).filter(
        models.SwapHistory.subscription_id.in_(subscription_ids)
    ).order_by(models.SwapHistory.timestamp.desc()).all()
    
    return swaps
