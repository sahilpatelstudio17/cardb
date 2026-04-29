from datetime import datetime, timedelta
import json
from typing import Optional
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from app import models, schemas
from app.core.security import create_access_token
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()


def create_user(db: Session, user_in: schemas.UserCreate):
    hashed = get_password_hash(user_in.password)
    user = models.User(email=user_in.email, full_name=user_in.full_name, hashed_password=hashed)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str):
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token_for_user(user: models.User):
    data = {"sub": str(user.id), "email": user.email, "is_admin": user.is_admin}
    token = create_access_token(data)
    return token


def get_available_cars(db: Session):
    return db.query(models.Car).filter(models.Car.available == True).all()


def get_car(db: Session, car_id: int):
    """Get a single car by ID"""
    return db.query(models.Car).filter(models.Car.id == car_id).first()


def get_active_subscription_car_ids(
    db: Session,
    subscription: models.Subscription,
    include_pending_returns: bool = True,
    exclude_return_request_id: Optional[int] = None,
):
    """Return active car ids for a subscription after swaps/returns are applied."""
    if not subscription:
        return []

    car_timestamps = {}

    def track_car(car_id: Optional[int], seen_at):
        if not car_id:
            return
        normalized_seen_at = seen_at or subscription.start_date or datetime.utcnow()
        previous_seen_at = car_timestamps.get(car_id)
        if previous_seen_at is None or normalized_seen_at > previous_seen_at:
            car_timestamps[car_id] = normalized_seen_at

    track_car(subscription.car_id, subscription.start_date)

    approved_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == subscription.user_id,
        models.Booking.status == "approved",
    ).all()
    for booking in approved_bookings:
        if subscription.start_date and booking.created_at and booking.created_at < subscription.start_date:
            continue
        track_car(booking.car_id, booking.created_at)

    approved_swaps = db.query(models.SwapHistory).filter(
        models.SwapHistory.subscription_id == subscription.id,
        models.SwapHistory.status == "approved",
    ).all()

    swapped_from_ids = set()
    for swap in approved_swaps:
        track_car(swap.to_car_id, swap.timestamp)
        if swap.from_car_id:
            swapped_from_ids.add(swap.from_car_id)

    return_statuses = ["approved"]
    if include_pending_returns:
        return_statuses.append("pending")

    return_requests_query = db.query(models.ReturnRequest).filter(
        models.ReturnRequest.subscription_id == subscription.id,
        models.ReturnRequest.status.in_(return_statuses),
    )
    if exclude_return_request_id is not None:
        return_requests_query = return_requests_query.filter(models.ReturnRequest.id != exclude_return_request_id)

    latest_return_timestamps = {}
    for return_request in return_requests_query.all():
        if not return_request.car_id:
            continue
        return_seen_at = return_request.updated_at or return_request.created_at or datetime.utcnow()
        previous_seen_at = latest_return_timestamps.get(return_request.car_id)
        if previous_seen_at is None or return_seen_at > previous_seen_at:
            latest_return_timestamps[return_request.car_id] = return_seen_at

    active_car_entries = [
        (car_id, seen_at)
        for car_id, seen_at in car_timestamps.items()
        if car_id not in swapped_from_ids and (
            car_id not in latest_return_timestamps or seen_at > latest_return_timestamps[car_id]
        )
    ]
    active_car_entries.sort(key=lambda item: item[1], reverse=True)
    return [car_id for car_id, _ in active_car_entries]


def get_active_user_car_ids(
    db: Session,
    user_id: int,
    include_pending_returns: bool = True,
    exclude_return_request_id: Optional[int] = None,
):
    """Return active car ids for a user across bookings/swaps/subscriptions."""
    car_timestamps = {}

    def track_car(car_id: Optional[int], seen_at):
        if not car_id:
            return
        normalized_seen_at = seen_at or datetime.utcnow()
        previous_seen_at = car_timestamps.get(car_id)
        if previous_seen_at is None or normalized_seen_at > previous_seen_at:
            car_timestamps[car_id] = normalized_seen_at

    active_subscriptions = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id,
        models.Subscription.active == True,
    ).all()
    for subscription in active_subscriptions:
        track_car(subscription.car_id, subscription.start_date)

    approved_bookings = db.query(models.Booking).filter(
        models.Booking.user_id == user_id,
        models.Booking.status == "approved",
    ).all()
    for booking in approved_bookings:
        track_car(booking.car_id, booking.created_at)

    user_subscriptions = db.query(models.Subscription).filter(
        models.Subscription.user_id == user_id
    ).all()
    user_subscription_ids = [subscription.id for subscription in user_subscriptions]

    swapped_from_ids = set()
    if user_subscription_ids:
        approved_swaps = db.query(models.SwapHistory).filter(
            models.SwapHistory.subscription_id.in_(user_subscription_ids),
            models.SwapHistory.status == "approved",
        ).all()
        for swap in approved_swaps:
            track_car(swap.to_car_id, swap.timestamp)
            if swap.from_car_id:
                swapped_from_ids.add(swap.from_car_id)

    return_statuses = ["approved"]
    if include_pending_returns:
        return_statuses.append("pending")

    return_requests_query = db.query(models.ReturnRequest).filter(
        models.ReturnRequest.user_id == user_id,
        models.ReturnRequest.status.in_(return_statuses),
    )
    if exclude_return_request_id is not None:
        return_requests_query = return_requests_query.filter(models.ReturnRequest.id != exclude_return_request_id)

    latest_return_timestamps = {}
    for return_request in return_requests_query.all():
        if not return_request.car_id:
            continue
        return_seen_at = return_request.updated_at or return_request.created_at or datetime.utcnow()
        previous_seen_at = latest_return_timestamps.get(return_request.car_id)
        if previous_seen_at is None or return_seen_at > previous_seen_at:
            latest_return_timestamps[return_request.car_id] = return_seen_at

    active_car_entries = [
        (car_id, seen_at)
        for car_id, seen_at in car_timestamps.items()
        if car_id not in swapped_from_ids and (
            car_id not in latest_return_timestamps or seen_at > latest_return_timestamps[car_id]
        )
    ]
    active_car_entries.sort(key=lambda item: item[1], reverse=True)
    return [car_id for car_id, _ in active_car_entries]


def create_car(db: Session, car_in: schemas.CarCreate):
    car = models.Car(brand=car_in.brand, name=car_in.name, image=car_in.image, available=car_in.available)
    db.add(car)
    db.commit()
    db.refresh(car)
    return car


def create_subscription(db: Session, user: models.User, car_id: int, plan_id: int, needs_driver: bool = False, driver_service_details=None):
    car = db.query(models.Car).filter(models.Car.id == car_id).first()
    if not car or not car.available:
        raise ValueError("Car is not available")
    plan = db.query(models.SubscriptionPlan).filter(models.SubscriptionPlan.id == plan_id).first()
    if not plan:
        raise ValueError("Invalid plan")
    # create subscription
    import datetime
    start = datetime.datetime.utcnow()
    end = start + timedelta(days=30 * plan.duration_months)
    subscription = models.Subscription(
        user_id=user.id,
        car_id=car.id,
        plan_id=plan.id,
        needs_driver=needs_driver,
        driver_service_details=json.dumps(driver_service_details) if driver_service_details else None,
        start_date=start,
        end_date=end,
        active=True
    )
    car.available = False
    db.add(subscription)
    db.commit()
    db.refresh(subscription)
    return subscription


def swap_subscription(db: Session, user: models.User, subscription_id: int, to_car_id: int, note: str = None):
    subscription = db.query(models.Subscription).filter(models.Subscription.id == subscription_id, models.Subscription.user_id == user.id).first()
    if not subscription:
        raise ValueError("Subscription not found")
    
    # check if subscription is active
    if not subscription.active:
        raise ValueError("Subscription is not active")
    
    plan = subscription.plan
    if plan and subscription.swaps_count >= plan.swap_limit:
        raise ValueError("Swap limit reached for your plan")
    to_car = db.query(models.Car).filter(models.Car.id == to_car_id).first()
    if not to_car or not to_car.available:
        raise ValueError("Target car not available")
    # perform swap
    from_car_id = subscription.car_id
    old_car = db.query(models.Car).filter(models.Car.id == from_car_id).first()
    if old_car:
        old_car.available = True
    to_car.available = False
    subscription.car_id = to_car.id
    subscription.swaps_count = subscription.swaps_count + 1
    # record history
    swap = models.SwapHistory(subscription_id=subscription.id, from_car_id=from_car_id, to_car_id=to_car.id, note=note)
    db.add(swap)
    db.commit()
    db.refresh(swap)
    return swap
