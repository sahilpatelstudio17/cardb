from datetime import datetime, timedelta
from enum import Enum as PyEnum

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float, Enum
from sqlalchemy.orm import relationship
from app.core.database import Base


# Enums for status tracking
class BookingStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SwapStatus(str, PyEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class CarCategory(str, PyEnum):
    SEDAN = "Sedan"
    SUV = "SUV"
    HATCHBACK = "Hatchback"
    LUXURY = "Luxury"
    SPORTS = "Sports"


class PlanTier(str, PyEnum):
    BASIC = "basic"
    PREMIUM = "premium"
    LUXURY = "luxury"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="user")
    bookings = relationship("Booking", back_populates="user")
    return_requests = relationship("ReturnRequest", back_populates="user")


class Car(Base):
    __tablename__ = "cars"
    id = Column(Integer, primary_key=True, index=True)
    brand = Column(String(100), nullable=False)
    name = Column(String(100), nullable=False)
    image = Column(String(255), nullable=True)
    category = Column(String(50), default="Sedan")
    required_plan = Column(String(50), default="basic")  # basic, premium, luxury
    available = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="car")
    bookings = relationship("Booking", back_populates="car")

class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    price = Column(Float, default=0.0)
    duration_months = Column(Integer, default=1)
    swap_limit = Column(Integer, default=0)  # number of swaps allowed
    tier = Column(String(50), default="basic")  # basic, premium, luxury
    features = Column(Text, nullable=True)  # JSON string of features
    max_active_bookings = Column(Integer, default=1)  # max concurrent bookings
    created_at = Column(DateTime, default=datetime.utcnow)

    subscriptions = relationship("Subscription", back_populates="plan")


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"))
    plan_id = Column(Integer, ForeignKey("subscription_plans.id", ondelete="SET NULL"))
    needs_driver = Column(Boolean, default=False, nullable=False)
    driver_service_details = Column(Text, nullable=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    swaps_count = Column(Integer, default=0)

    user = relationship("User", back_populates="subscriptions")
    car = relationship("Car", back_populates="subscriptions")
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")
    swaps = relationship("SwapHistory", back_populates="subscription")
    return_requests = relationship("ReturnRequest", back_populates="subscription")


class Booking(Base):
    __tablename__ = "bookings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"), nullable=False)
    status = Column(String(50), default="pending")  # pending, approved, rejected
    request_type = Column(String(50), default="booking")  # booking, swap
    note = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="bookings")
    car = relationship("Car", back_populates="bookings")


class SwapHistory(Base):
    __tablename__ = "swap_history"
    id = Column(Integer, primary_key=True, index=True)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    from_car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"))
    to_car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"))
    status = Column(String(50), default="pending")  # pending, approved, rejected
    timestamp = Column(DateTime, default=datetime.utcnow)
    note = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)

    subscription = relationship("Subscription", back_populates="swaps")


class ReturnRequest(Base):
    __tablename__ = "return_requests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    car_id = Column(Integer, ForeignKey("cars.id", ondelete="SET NULL"))
    status = Column(String(50), default="pending")  # pending, approved, rejected
    reason = Column(Text, nullable=True)
    admin_note = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="return_requests")
    subscription = relationship("Subscription", back_populates="return_requests")
    car = relationship("Car", foreign_keys=[car_id])


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
