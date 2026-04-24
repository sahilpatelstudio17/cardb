from typing import List

import razorpay
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import crud, models, schemas
from app.core.config import settings
from app.deps import get_current_user, get_db_dep

router = APIRouter(prefix="/payments", tags=["payments"])

_plan_tier_order = {"basic": 1, "premium": 2, "luxury": 3}


def _validate_selection_for_plan(
    db: Session,
    user: models.User,
    plan: models.SubscriptionPlan,
    selected_car_ids: List[int],
):
    if not selected_car_ids:
        raise HTTPException(status_code=400, detail="Please select at least one car")

    if len(set(selected_car_ids)) != len(selected_car_ids):
        raise HTTPException(status_code=400, detail="Duplicate cars are not allowed")

    max_bookings = plan.max_active_bookings or 1
    if len(selected_car_ids) > max_bookings:
        raise HTTPException(
            status_code=400,
            detail=f"You can book up to {max_bookings} car(s) for this plan",
        )

    existing_active_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user.id,
        models.Booking.status.in_(["pending", "approved"]),
    ).count()

    if existing_active_bookings + len(selected_car_ids) > max_bookings:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Your {plan.name} plan allows only {max_bookings} active booking(s). "
                f"You already have {existing_active_bookings}."
            ),
        )

    user_tier = _plan_tier_order.get((plan.tier or "basic").lower(), 1)

    for car_id in selected_car_ids:
        car = db.query(models.Car).filter(models.Car.id == car_id).first()
        if not car:
            raise HTTPException(status_code=404, detail=f"Car with id {car_id} not found")

        car_required = _plan_tier_order.get((car.required_plan or "basic").lower(), 1)
        if user_tier < car_required:
            raise HTTPException(
                status_code=400,
                detail=f"{car.brand} {car.name} requires a {car.required_plan} plan or higher",
            )

        existing_pending = db.query(models.Booking).filter(
            models.Booking.user_id == user.id,
            models.Booking.car_id == car_id,
            models.Booking.status == "pending",
        ).first()

        if existing_pending:
            raise HTTPException(
                status_code=400,
                detail=f"You already have a pending booking for car id {car_id}",
            )


@router.post("/razorpay/order", response_model=schemas.RazorpayCreateOrderResponse)
def create_razorpay_order(
    req: schemas.RazorpayCreateOrderRequest,
    db: Session = Depends(get_db_dep),
    current_user: models.User = Depends(get_current_user),
):
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == req.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    _validate_selection_for_plan(db, current_user, plan, req.selected_car_ids)

    amount_in_paise = int(round(float(plan.price) * 100))
    if amount_in_paise <= 0:
        raise HTTPException(status_code=400, detail="Invalid plan amount")

    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        order = razorpay_client.order.create(
            {
                "amount": amount_in_paise,
                "currency": "INR",
                "payment_capture": 1,
                "notes": {
                    "user_id": str(current_user.id),
                    "plan_id": str(plan.id),
                },
            }
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Failed to create Razorpay order: {exc}")

    return schemas.RazorpayCreateOrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post(
    "/razorpay/verify-and-activate",
    response_model=schemas.RazorpayVerifyAndActivateResponse,
)
def verify_payment_and_activate(
    req: schemas.RazorpayVerifyAndActivateRequest,
    db: Session = Depends(get_db_dep),
    current_user: models.User = Depends(get_current_user),
):
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == req.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found")

    active_subscription = db.query(models.Subscription).filter(
        models.Subscription.user_id == current_user.id,
        models.Subscription.active == True,
    ).first()
    if active_subscription:
        raise HTTPException(status_code=400, detail="You already have an active subscription")

    _validate_selection_for_plan(db, current_user, plan, req.selected_car_ids)

    razorpay_client = razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )

    try:
        razorpay_client.utility.verify_payment_signature(
            {
                "razorpay_order_id": req.razorpay_order_id,
                "razorpay_payment_id": req.razorpay_payment_id,
                "razorpay_signature": req.razorpay_signature,
            }
        )
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid Razorpay payment signature")

    try:
        primary_car_id = req.selected_car_ids[0]
        subscription = crud.create_subscription(
            db,
            current_user,
            primary_car_id,
            req.plan_id,
            bool(req.driver_service_details),
            req.driver_service_details,
        )

        booking_ids: List[int] = []
        for car_id in req.selected_car_ids:
            booking = models.Booking(
                user_id=current_user.id,
                car_id=car_id,
                status="pending",
                request_type="booking",
                note="Paid via Razorpay",
            )
            db.add(booking)
            db.flush()
            booking_ids.append(booking.id)

        db.commit()

        return schemas.RazorpayVerifyAndActivateResponse(
            detail="Payment verified. Subscription activated and bookings created.",
            subscription_id=subscription.id,
            booking_ids=booking_ids,
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to activate subscription: {exc}")
