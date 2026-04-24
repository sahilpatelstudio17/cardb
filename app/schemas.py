from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr
from enum import Enum


class BookingStatusEnum(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str]
    is_admin: bool

    class Config:
        orm_mode = True


class CarBase(BaseModel):
    brand: str
    name: str
    image: Optional[str] = None
    category: Optional[str] = "Sedan"
    required_plan: Optional[str] = "basic"


class CarCreate(CarBase):
    available: Optional[bool] = True


class CarOut(CarBase):
    id: int
    available: bool
    created_at: datetime

    class Config:
        orm_mode = True


class SubscriptionPlanCreate(BaseModel):
    name: str
    price: float
    duration_months: int
    swap_limit: int
    tier: Optional[str] = "basic"
    features: Optional[str] = None
    max_active_bookings: Optional[int] = 1


class SubscriptionPlanOut(BaseModel):
    id: int
    name: str
    price: float
    duration_months: int
    swap_limit: int
    tier: Optional[str] = "basic"
    features: Optional[str] = None
    max_active_bookings: Optional[int] = 1
    created_at: datetime

    class Config:
        orm_mode = True


class SubscribeRequest(BaseModel):
    car_id: int
    plan_id: int
    needs_driver: Optional[bool] = False
    driver_service_details: Optional[Dict[str, Any]] = None


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    car: Optional[CarOut]
    plan: Optional[SubscriptionPlanOut]
    needs_driver: bool
    driver_service_details: Optional[str] = None
    start_date: datetime
    end_date: Optional[datetime]
    active: bool
    swaps_count: int

    class Config:
        orm_mode = True


# Booking schemas
class BookingCreate(BaseModel):
    car_id: int
    note: Optional[str] = None


class BookingOut(BaseModel):
    id: int
    user_id: int
    car_id: int
    status: str
    request_type: str
    note: Optional[str]
    admin_note: Optional[str]
    created_at: datetime
    updated_at: datetime
    car: Optional[CarOut] = None
    user: Optional[UserOut] = None

    class Config:
        orm_mode = True


class BookingApproval(BaseModel):
    admin_note: Optional[str] = None


class SwapRequest(BaseModel):
    subscription_id: int
    from_car_id: Optional[int] = None
    to_car_id: int
    note: Optional[str] = None


class SwapOut(BaseModel):
    id: int
    subscription_id: int
    from_car_id: Optional[int]
    to_car_id: Optional[int]
    status: Optional[str] = "pending"
    timestamp: datetime
    note: Optional[str]
    admin_note: Optional[str] = None

    class Config:
        orm_mode = True


class ContactCreate(BaseModel):
    name: str
    email: EmailStr
    message: str


class ContactOut(BaseModel):
    id: int
    name: str
    email: str
    message: str
    read: bool
    created_at: datetime

    class Config:
        orm_mode = True


class RazorpayCreateOrderRequest(BaseModel):
    plan_id: int
    selected_car_ids: List[int]
    driver_service_details: Optional[Dict[str, Any]] = None


class RazorpayCreateOrderResponse(BaseModel):
    order_id: str
    amount: int
    currency: str
    key_id: str


class RazorpayVerifyAndActivateRequest(BaseModel):
    razorpay_payment_id: str
    razorpay_order_id: str
    razorpay_signature: str
    plan_id: int
    selected_car_ids: List[int]
    driver_service_details: Optional[Dict[str, Any]] = None


class RazorpayVerifyAndActivateResponse(BaseModel):
    detail: str
    subscription_id: int
    booking_ids: List[int]
