# Read DB Secrets from .env (db connection postgresql, psycopg2)
# Create DB_Connection_URL using db secret
# Create SQLalchemy engine using the DB_Connection_URL
# Add file to be loaded inside "tests" directory
# Use pandas to read the file
# Use pandas to upload the data read from the file to db. See models.py to know the datatype for column used in table.

# To run thnis script
# Activate .venv
# cd api
# python tests/data_load.py
