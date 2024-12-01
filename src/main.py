from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta, timezone
from passlib.context import CryptContext
from sqlalchemy import desc, func, and_
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
import random
import redis
import jwt
import os

from src.recommendation import collaborative_filtering_cosine
from src.sql_server import get_db
from src.utils import send_email
from src.models import *



app = FastAPI() # App initalize

# Initialize Redis client
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST"),  # Use your Redis host, e.g., "127.0.0.1" or a cloud Redis instance
    port=os.getenv("REDIS_PORT"),         # Default Redis port
    db=0,              # Redis database index
    decode_responses=True  # Ensures Redis returns strings instead of bytes
)


origins = [
    "http://localhost:3000",  # React development server port
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# JWT settings
SECRET_KEY = "your_secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc)+ (expires_delta or timedelta(days=7))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

def admin_required(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return current_user


# User and Movie Models (Pydantic)
class UserCreate(BaseModel):
    user_name: str
    email: str
    password: str
    role: Optional[str] = 'user'
    is_2fa_enabled: Optional[bool] = True

class UserLogin(BaseModel):
    email: str
    password: str

class VerifyOTP(BaseModel):
    email: str
    otp: int

class ResendOTP(BaseModel):
    email: str

class Clearredis_client(BaseModel):
    email: str

class UserResponse(BaseModel):
    user_id: int
    user_name: str
    email: str
    role: str  # Default role is 'user', can be 'admin'

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse
    refresh_token: Optional[str] = None

class MovieResponse(BaseModel):
    movie_id: int
    title: str
    genre: Optional[str] = None
    release_year: Optional[int] = None
    director: Optional[str] = None
    duration_min: Optional[int] = None
    poster: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    rating: Optional[int]

    class Config:
        orm_mode = True

# Pydantic schema for User
class UserSchema(BaseModel):
    user_id: int
    user_name: str
    email: str
    role: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class MoviesResponse(BaseModel):
    movies: List[MovieResponse]
    total: int

# Pydantic models for requests and responses
class RatingCreate(BaseModel):
    user_id: int
    movie_id: int
    rating: float

class RatingResponse(BaseModel):
    id: int
    user_id: int
    movie_id: int
    rating: float
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# Pydantic models for adding/updating movies
class MovieCreate(BaseModel):
    title: str
    genre: str
    release_year: int
    director: str
    duration_min: int
    poster: str

class MovieUpdate(BaseModel):
    title: Optional[str]
    genre: Optional[str]
    release_year: Optional[int]
    director: Optional[str]
    duration_min: Optional[int]
    poster: Optional[str]

# 1. User Signup Endpoint
@app.post("/signup/")
def signup(user: UserCreate, db: Session = Depends(get_db)):
    # Check if user already exists
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user
    new_user = User(
        user_name=user.user_name,
        email=user.email,
        password=hash_password(user.password),
        role = user.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.user_id}


# 2. Login endpoint
@app.post("/login")
def login_for_access_token(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    
    # Check if 2FA is enabled
    if not db_user.is_2fa_enabled:
        return {"message": "Two-Factor Authentication (2FA) is not enabled. Please enable it to continue."}
    
    # Generate a 2FA OTP
    otp = random.randint(100000, 999999)  # Example: 6-digit OTP
    # Store the OTP (e.g., Redis or in-memory)
    redis_client.set(f"otp:{db_user.email}", otp, ex=300)  # Store OTP for 5 minutes

    # Send OTP via email
    send_email(
        to_email=db_user.email,
        subject="Your 2FA OTP",
        body=f"Your OTP is: {otp}. It expires in 5 minutes."
    )
    return {"message": "OTP sent to your email"}
    

@app.post("/resend-otp")
def resend_otp(data: ResendOTP, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if 2FA is enabled
    if not db_user.is_2fa_enabled:
        return {"message": "Two-Factor Authentication (2FA) is not enabled. Please enable it to continue."}
    
    # Generate a 2FA OTP
    otp = random.randint(100000, 999999)  # Example: 6-digit OTP
    # Store the OTP (e.g., Redis or in-memory)
    redis_client.set(f"otp:{db_user.email}", otp, ex=300)  # Store OTP for 5 minutes

    # Send OTP via email
    send_email(
        to_email=db_user.email,
        subject="Your 2FA OTP",
        body=f"Your OTP is: {otp}. It expires in 5 minutes."
    )
    return {"message": "OTP resent to your email"}


# End point to verify the OTP sent to user's email
@app.post("/verify-otp")
def verify_otp(data: VerifyOTP, db: Session = Depends(get_db)):
    # Retrieve stored OTP
    stored_otp = redis_client.get(f"otp:{data.email}")
    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or invalid")
    if int(stored_otp) != data.otp:
        print(stored_otp)
        raise HTTPException(status_code=401, detail="Invalid OTP")

    # If OTP is valid, generate tokens
    db_user = db.query(User).filter(User.email == data.email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    access_token = create_access_token(data={"sub": data.email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    refresh_token = create_refresh_token(data={"sub": data.email}, expires_delta=timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS))

    # Clear OTP after successful verification
    redis_client.delete(f"otp:{data.email}")

    user_data = UserResponse(
        user_id=db_user.user_id,
        user_name=db_user.user_name,
        email=db_user.email,
        role=db_user.role
    )
    return {"message": "User logged in successfully", "access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token, "user": user_data}

# End point to enable twi factor authentication
@app.post("/enable-2fa")
def enable_2fa(email: str, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == email).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db_user.is_2fa_enabled = True
    db.commit()
    return {"message": "Two-Factor Authentication (2FA) has been enabled for your account."}

# 4. Refresh token endpoint
@app.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str):
    try:
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        new_access_token = create_access_token(data={"sub": email}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
        return {"access_token": new_access_token, "token_type": "bearer"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

# 5. Get current user endpoint
@app.get("/users/me", response_model=UserSchema)
def get_user_me(current_user: User = Depends(get_current_user)):
    # This function returns the current authenticated user details
    return current_user

# 5. Get recommended movies for each user
@app.get("/recommendations/{user_id}")
def get_user_recommendations(user_id: int, db: Session = Depends(get_db)):
    # Fetch active recommendations for the user with left join on Rating table
    active_recommendations = (
        db.query(Recommendation, Movie, Rating)
        .join(Movie, Recommendation.movie_id == Movie.movie_id)
        .outerjoin(Rating, and_(Rating.movie_id == Recommendation.movie_id, Rating.user_id == user_id))
        .filter(Recommendation.user_id == user_id, Recommendation.active == True)
        .limit(10)
        .all()
    )

    # If active recommendations are found, return them
    if active_recommendations:
        recommendations = [
            {"movie_id": rec.movie_id, "title": movie.title, "poster": movie.poster, "recommended_at": rec.recommended_at, "rating": rating.rating if rating else None}
            for rec, movie, rating  in active_recommendations
        ]
        return {"recommendations": recommendations, "is_new_user": False}

    # If no active recommendations, fetch top 10 highest-rated movies
    top_movies = (
        db.query(Movie)
        .join(Rating, Rating.movie_id == Movie.movie_id)
        .group_by(Movie.movie_id)
        .order_by(desc(func.avg(Rating.rating)))
        .limit(10)
        .all()
    )

    # Prepare the fallback recommendations (top 10 movies)
    fallback_recommendations = [
        {"movie_id": movie.movie_id, "title": movie.title, "poster": movie.poster, "rating": db.query(func.avg(Rating.rating)).filter(Rating.movie_id == movie.movie_id).scalar()}
        for movie in top_movies
    ]
    
    return {"recommendations": fallback_recommendations, "is_new_user": True}

# 7. Update recommendation for users
@app.post("/recommendations/update")
def update_recommendations(db: Session = Depends(get_db)):
    # Retrieve all ratings from the database
    ratings = db.query(Rating).all()
    # Get recommendations using cosine similarity collaborative filtering
    recommendations = collaborative_filtering_cosine(ratings)

    for user_id, recommended_movies in recommendations.items():
        # Retrieve the user's current active recommendations
        current_recommendations = (
            db.query(Recommendation)
            .filter(Recommendation.user_id == user_id, Recommendation.active == True)
            .order_by(Recommendation.recommended_at)
            .all()
        )

        # Keep track of the number of new recommendations added
        num_new_recommendations = 0

        for movie_id in recommended_movies:
            # Check if the movie is already recommended
            if any(rec.movie_id == movie_id for rec in current_recommendations):
                continue

            # Add new recommendation
            new_recommendation = Recommendation(
                user_id=user_id,
                movie_id=movie_id,
                recommended_at=datetime.utcnow(),
                interacted=0,
                active=True
            )
            db.add(new_recommendation)
            db.commit()
            num_new_recommendations += 1

            # If more than 20 recommendations, deactivate the oldest
            if len(current_recommendations) + num_new_recommendations > 20:
                oldest_recommendation = current_recommendations.pop(0)
                oldest_recommendation.active = False
                db.commit()

    return {"message": "Recommendations updated successfully"}

# 8. Search Movies by Title
@app.get("/movies/search/", response_model=List[MovieResponse])
def search_movies(query: str, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    searched_movies = db.query(Movie).filter(Movie.title.contains(query)).all()
    return searched_movies

# 9. Get All Movies with Pagination
@app.get("/movies/", response_model=MoviesResponse)
def read_movies(skip: int = 0, limit: int = 10, search: Optional[str] = None, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Query movies with average ratings
    query = db.query(
        Movie.movie_id,
        Movie.title,
        Movie.genre,
        Movie.release_year,
        Movie.director,
        Movie.duration_min,
        Movie.poster,
        Movie.created_at,
        Movie.updated_at,
        func.avg(Rating.rating).label("average_rating")  # Calculate average rating
    ).outerjoin(
        Rating, Movie.movie_id == Rating.movie_id  # Left join movies with ratings
    ).group_by(
        Movie.movie_id  # Group by movie id to calculate average ratings
    ).order_by(
        Movie.title  # Optional: Order the result by movie title
    )

    # Apply search filter if provided
    if search:
        query = query.filter(Movie.title.ilike(f"%{search}%"))

    # Get total count and paginated results
    total = query.count()  # Total number of results
    movies = query.offset(skip).limit(limit).all()  # Paginated results

    # Format results to match the response model
    formatted_movies = [
        MovieResponse(
            movie_id=movie.movie_id,
            title=movie.title,
            genre=movie.genre,
            release_year=movie.release_year,
            director=movie.director,
            duration_min=movie.duration_min,
            poster=movie.poster,
            created_at=movie.created_at,
            updated_at=movie.updated_at,
            rating=movie.average_rating,  # Average rating or None
        )
        for movie in movies
    ]

    return {"movies": formatted_movies, "total": total}

# 10. Add a new rating by user
@app.post("/ratings", response_model=RatingResponse)
def add_rating(rating: RatingCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Check if the user has already rated this movie
    existing_rating = db.query(Rating).filter(
        Rating.user_id == rating.user_id,
        Rating.movie_id == rating.movie_id
    ).first()

    if existing_rating:
        raise HTTPException(status_code=400, detail="User has already rated this movie")

    # Add the new rating
    new_rating = Rating(
        user_id=rating.user_id,
        movie_id=rating.movie_id,
        rating=rating.rating
    )
    db.add(new_rating)
    db.commit()
    db.refresh(new_rating)
    return new_rating

# 11. Update an existing rating
@app.put("/ratings/{rating_id}", response_model=RatingResponse)
def update_rating(rating_id: int, rating: RatingCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    # Find the rating by ID
    db_rating = db.query(Rating).filter(Rating.id == rating_id).first()
    if not db_rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    # Update the rating value
    db_rating.rating = rating.rating
    db.commit()
    db.refresh(db_rating)
    return db_rating

# 12. Get all ratings for a specific movie
@app.get("/movies/{movie_id}/ratings", response_model=List[RatingResponse])
def get_movie_ratings(movie_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ratings = db.query(Rating).filter(Rating.movie_id == movie_id).all()
    return ratings

# 13. Get all ratings given by a specific user
@app.get("/users/{user_id}/ratings", response_model=List[RatingResponse])
def get_user_ratings(user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    return ratings

# 14. Add a new movie (Admin only)
@app.post("/admin/movies/", dependencies=[Depends(admin_required)])
def add_movie(movie: MovieCreate, db: Session = Depends(get_db)):
    new_movie = Movie(
        title=movie.title,
        genre=movie.genre,
        release_year=movie.release_year,
        director=movie.director,
        duration_min=movie.duration_min,
        poster=movie.poster
    )
    db.add(new_movie)
    db.commit()
    db.refresh(new_movie)
    return new_movie

# 15. Update an existing movie (Admin only)
@app.put("/admin/movies/{movie_id}", dependencies=[Depends(admin_required)])
def update_movie(movie_id: int, movie: MovieUpdate, db: Session = Depends(get_db)):
    db_movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    # Update the fields that were provided
    if movie.title:
        db_movie.title = movie.title
    if movie.genre:
        db_movie.genre = movie.genre
    if movie.release_year:
        db_movie.release_year = movie.release_year
    if movie.director:
        db_movie.director = movie.director
    if movie.duration_min:
        db_movie.duration_min = movie.duration_min
    if movie.poster:
        db_movie.poster = movie.poster
    
    db.commit()
    db.refresh(db_movie)
    return db_movie

# 16. Delete a movie (Admin only)
@app.delete("/admin/movies/{movie_id}", dependencies=[Depends(admin_required)])
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    db_movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    db.delete(db_movie)
    db.commit()
    return {"message": "Movie deleted successfully"}

# 17. Delete a user (Admin only)
@app.delete("/admin/users/{user_id}", dependencies=[Depends(admin_required)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}


# 18. Get all users (Admin only)
@app.get("/admin/users")
def delete_user(db: Session = Depends(get_db)):
    db_users = db.query(User).all()
    if not db_users:
        raise HTTPException(status_code=404, detail="No user found")
    
    return {"users": db_users}
