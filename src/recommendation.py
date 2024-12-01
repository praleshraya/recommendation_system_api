from sklearn.metrics.pairwise import cosine_similarity
import pandas as pd


# Collaborative filtering recommendation function using cosine similarity
def collaborative_filtering_cosine(ratings):
    # Convert ratings to a pandas DataFrame for easier manipulation
    ratings_df = pd.DataFrame([{
        "user_id": rating.user_id,
        "movie_id": rating.movie_id,
        "rating": rating.rating
    } for rating in ratings])

    # Create the user-movie rating matrix
    user_movie_matrix = ratings_df.pivot_table(index="user_id", columns="movie_id", values="rating").fillna(0)

    # Calculate cosine similarity between users
    user_similarity = cosine_similarity(user_movie_matrix)
    user_similarity_df = pd.DataFrame(user_similarity, index=user_movie_matrix.index, columns=user_movie_matrix.index)

    # Dictionary to hold recommendations for each user
    recommendations = {}

    # Generate recommendations for each user
    for user_id in user_movie_matrix.index:
        # Identify similar users for the target user
        similar_users = user_similarity_df[user_id].sort_values(ascending=False).index[1:]

        # Get the target user's rated movies
        user_rated_movies = user_movie_matrix.loc[user_id]
        user_watched_movies = set(user_rated_movies[user_rated_movies > 0].index)

        # Calculate weighted average ratings from similar users
        weighted_ratings = pd.Series(dtype=float)

        for similar_user in similar_users:
            # Get ratings from the similar user
            similar_user_ratings = user_movie_matrix.loc[similar_user]
            # Only consider movies that the target user hasn't watched
            similar_user_unwatched_ratings = similar_user_ratings[similar_user_ratings.index.difference(user_watched_movies)]
            # Weight the ratings by similarity
            weighted_ratings = weighted_ratings.add(similar_user_unwatched_ratings * user_similarity_df.loc[user_id, similar_user], fill_value=0)

        # Get the top 20 recommended movie IDs based on weighted ratings
        top_recommendations = weighted_ratings.sort_values(ascending=False).head(20).index.tolist()

        # Store the recommendations
        recommendations[user_id] = top_recommendations

    return recommendations
