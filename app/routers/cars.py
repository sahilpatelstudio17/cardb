from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from app import schemas, crud, models
from app.deps import get_db_dep, get_current_user

router = APIRouter()


@router.get("/cars", response_model=List[schemas.CarOut])
def list_cars(db: Session = Depends(get_db_dep)):
    cars = crud.get_available_cars(db)
    return cars


@router.get("/cars/{car_id}", response_model=schemas.CarOut)
def get_car_by_id(car_id: int, db: Session = Depends(get_db_dep)):
    """Get a single car by ID"""
    from fastapi import HTTPException
    car = crud.get_car(db, car_id)
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")
    return car


@router.get("/cars/all", response_model=List[schemas.CarOut])
def list_all_cars(db: Session = Depends(get_db_dep)):
    """List all cars including unavailable ones"""
    cars = db.query(models.Car).all()
    return cars


@router.get("/me", response_model=schemas.UserOut)
def get_current_user_info(current_user: models.User = Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.post("/contact", response_model=schemas.ContactOut)
def submit_contact(contact: schemas.ContactCreate, db: Session = Depends(get_db_dep)):
    """Submit a contact message (public endpoint)"""
    contact_msg = models.ContactMessage(
        name=contact.name,
        email=contact.email,
        message=contact.message
    )
    db.add(contact_msg)
    db.commit()
    db.refresh(contact_msg)
    return contact_msg
