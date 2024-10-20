from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from passlib.context import CryptContext
from typing import List, Optional
from sqlalchemy.orm import Session
from pydantic import BaseModel

from src.sql_server import get_db
from src.models import *

app = FastAPI() # App initalize


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

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Helper function to hash passwords
def hash_password(password: str):
    return pwd_context.hash(password)

# Helper function to verify passwords
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

# Assuming we have a method to get the current user from the token
def fake_get_current_user():
    # Simulating an admin user
    return {"user_id": 1, "role": "admin"}

def admin_required(current_user=Depends(fake_get_current_user)):
    if current_user["role"] != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user


# User and Movie Models (Pydantic)
class UserCreate(BaseModel):
    user_name: str
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class MovieResponse(BaseModel):
    title: str
    genre: str
    release_year: int
    director: str
    duration_min: int
    poster: str
    created_at: str
    updated_at: str

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
    created_at: str
    updated_at: str

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
        password=hash_password(user.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"message": "User created successfully", "user_id": new_user.user_id}

# 2. User Login Endpoint
@app.post("/login/")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(status_code=400, detail="Invalid email or password")
    
    # Generate a token or return login success
    return {"message": "Login successful", "user": db_user}

# # 3. Get Top 10 Movies for New Users
# @app.get("/movies/recommendations/top10/", response_model=List[Movie])
# def get_top_10_movies(db: Session = Depends(get_db)):
#     top_movies = db.query(models.Movie).order_by(models.Movie.id).limit(10).all()
#     return top_movies

# # 4. Get Similar Movies for Existing Users
# @app.get("/movies/recommendations/similar/{user_id}/", response_model=List[Movie])
# def get_similar_movies(user_id: int, db: Session = Depends(get_db)):
#     # This is a placeholder for your recommendation logic
#     similar_movies = db.query(models.Movie).order_by(models.Movie.id.desc()).limit(10).all()
#     return similar_movies

# 5. Search Movies by Title
@app.get("/movies/search/", response_model=List[MovieResponse])
def search_movies(query: str, db: Session = Depends(get_db)):
    searched_movies = db.query(Movie).filter(Movie.title.contains(query)).all()
    return searched_movies

# 6. Get All Movies with Pagination
@app.get("/movies/", response_model=List[MovieResponse])
def get_movies(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    all_movies = db.query(Movie).offset(skip).limit(limit).all()
    return all_movies

# 7. Add a new rating
@app.post("/ratings/", response_model=RatingResponse)
def add_rating(rating: RatingCreate, db: Session = Depends(get_db)):
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

# 8. Update an existing rating
@app.put("/ratings/{rating_id}", response_model=RatingResponse)
def update_rating(rating_id: int, rating: RatingCreate, db: Session = Depends(get_db)):
    # Find the rating by ID
    db_rating = db.query(Rating).filter(Rating.id == rating_id).first()
    if not db_rating:
        raise HTTPException(status_code=404, detail="Rating not found")

    # Update the rating value
    db_rating.rating = rating.rating
    db.commit()
    db.refresh(db_rating)
    return db_rating

# 9. Get all ratings for a specific movie
@app.get("/movies/{movie_id}/ratings", response_model=List[RatingResponse])
def get_movie_ratings(movie_id: int, db: Session = Depends(get_db)):
    ratings = db.query(Rating).filter(Rating.movie_id == movie_id).all()
    return ratings

# 10. Get all ratings given by a specific user
@app.get("/users/{user_id}/ratings", response_model=List[RatingResponse])
def get_user_ratings(user_id: int, db: Session = Depends(get_db)):
    ratings = db.query(Rating).filter(Rating.user_id == user_id).all()
    return ratings

# 11. Add a new movie (Admin only)
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

# 12. Update an existing movie (Admin only)
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

# 13. Delete a movie (Admin only)
@app.delete("/admin/movies/{movie_id}", dependencies=[Depends(admin_required)])
def delete_movie(movie_id: int, db: Session = Depends(get_db)):
    db_movie = db.query(Movie).filter(Movie.movie_id == movie_id).first()
    if not db_movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    db.delete(db_movie)
    db.commit()
    return {"message": "Movie deleted successfully"}

# 14. Delete a user (Admin only)
@app.delete("/admin/users/{user_id}", dependencies=[Depends(admin_required)])
def delete_user(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(db_user)
    db.commit()
    return {"message": "User deleted successfully"}
