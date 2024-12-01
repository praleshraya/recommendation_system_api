from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import text
from sqlalchemy import event


from src.sql_server import Base


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    password = Column(String)
    role = Column(String, default="user")  # Default role is 'user', can be 'admin'
    is_2fa_enabled = Column(Boolean, default=True)  # New column for 2FA
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    ratings = relationship("Rating", back_populates="user")
    user_movies = relationship("UserMovie", back_populates="user")


class Movie(Base):
    __tablename__ = "movies"

    movie_id = Column(Integer, primary_key=True, autoincrement=True, index=True)  # Primary Key
    title = Column(String, index=True)  # Movie title
    genre = Column(String)  # Movie genre
    release_year = Column(Integer)  # Year of release
    director = Column(String)  # Director's name
    duration_min = Column(Integer)  # Movie duration in minutes
    poster = Column(String)  # URL to poster image
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Auto-created timestamp
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())  # Auto-updated timestamp

    ratings = relationship("Rating", back_populates="movie")
    user_movies = relationship("UserMovie", back_populates="movie")


class Rating(Base):
    __tablename__ = "ratings"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    movie_id = Column(Integer, ForeignKey("movies.movie_id"))
    rating = Column(Float)  # Rating can be a float value (e.g., 4.5 out of 5)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="ratings")
    movie = relationship("Movie", back_populates="ratings")


class UserMovie(Base):
    __tablename__ = "user_movies"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    movie_id = Column(Integer, ForeignKey("movies.movie_id"))
    interaction_type = Column(String)  # e.g., 'watched', 'liked', 'favorited'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="user_movies")
    movie = relationship("Movie", back_populates="user_movies")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    movie_id = Column(Integer, ForeignKey("movies.movie_id"))
    recommended_at = Column(DateTime(timezone=True), server_default=func.now())
    interacted = Column(Integer, default=0)  # Whether the user interacted with the recommendation (1 = yes, 0 = no)
    active = Column(Boolean, default=True)  # New column

    # Relationships
    user = relationship("User")
    movie = relationship("Movie")

# Automatically update `updated_at` before an update on the Rating table
@event.listens_for(Rating, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = func.now()

# Automatically set the updated_at on any update
@event.listens_for(User, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = func.now()

@event.listens_for(Movie, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = func.now()

@event.listens_for(UserMovie, 'before_update')
def receive_before_update(mapper, connection, target):
    target.updated_at = func.now()
