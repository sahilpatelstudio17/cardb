from datetime import timedelta
import json
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
