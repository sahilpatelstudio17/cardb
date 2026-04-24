# """
# Database initialization script to seed test data.
# Run this once to populate the database with subscription plans and cars.
# """

# from sqlalchemy import text

# from app import models
# from app.core.database import Base, SessionLocal, engine

# # Create all tables
# Base.metadata.create_all(bind=engine)

# db = SessionLocal()

# # Clear existing data and reset auto-increment IDs
# db.execute(
#     text(
#         "TRUNCATE TABLE swap_history, subscriptions, cars, subscription_plans "
#         "RESTART IDENTITY CASCADE;"
#     )
# )

# # Create subscription plans
# plans = [
#     models.SubscriptionPlan(name="Basic", price=9999, duration_months=1, swap_limit=2, tier="basic", max_active_bookings=1),
#     models.SubscriptionPlan(name="Premium", price=13999, duration_months=1, swap_limit=5, tier="premium", max_active_bookings=2),
#     models.SubscriptionPlan(name="Luxury", price=19999, duration_months=1, swap_limit=7, tier="luxury", max_active_bookings=3),
# ]

# # Create 7 demo cars (IDs will be 1..7 after RESTART IDENTITY)
# cars = [
#     models.Car(brand="BMW", name="X5", image=None, available=True, required_plan="luxury", category="SUV"),
#     models.Car(brand="Hyundai", name="Creta", image=None, available=True, required_plan="premium", category="SUV"),
#     models.Car(brand="Maruti", name="Swift", image=None, available=True, required_plan="basic", category="Hatchback"),
#     models.Car(brand="Honda", name="City", image=None, available=True, required_plan="basic", category="Sedan"),
#     models.Car(brand="Skoda", name="Superb", image=None, available=True, required_plan="premium", category="Sedan"),
#     models.Car(brand="Toyota", name="Fortuner", image=None, available=True, required_plan="luxury", category="SUV"),
#     models.Car(brand="Audi", name="A6", image=None, available=True, required_plan="premium", category="Luxury"),
# ]

# db.add_all(plans)
# db.add_all(cars)
# db.commit()

# print("Database initialized with 7 demo cars and reset IDs")
# db.close()
