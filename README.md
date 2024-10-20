# Project Setup
1. clone the repository
``` bash
git clone git@github.com:praleshraya/recommendation_system_api.git
```
2. Go to project directory
```bash
cd recommendation_system_api/api
```

3. Create a virtual environment named ".venv"
```bash
python3 -m venv .venv
```

4. Activate virtual environment.
```bash
source .venv/bin/activate (linux)

.venv/Scripts/activate (windows)
```

5. Install dependencies.
```bash
pip install -r requirements.txt
```


# Database setup
1. Install PostgreSQL db (if not installed in your system)

2. Starting DB server
```bash
sudo systemctl start postgresql
```

3. Stopping DB server
```bash
sudo systemctl stop postgresql
```

4. Log in to PostgreSQL as the postgres User
```bash
sudo -i -u postgres
psql
```
5. Create a User
```sql
CREATE USER user_name WITH PASSWORD 'password';
```

6. Create Database
```sql
CREATE DATABASE recommendation_system;
```

7. Grant permission to newly created user to access the db
```sql
GRANT ALL PRIVILEGES ON DATABASE recommendation_system TO user_name;
```
8. To exit
```sql
\q
```

9. Test db connection from newly created user and pw:
```bash
psql -U user_name -d recommendation_system -h localhost -W
```

# Running migrations in DB
1. Make sure the db is up and running
```bash
sudo systemctl status postgresql
```

2. Go to your project directory. Inside your project directory, run following command. NOTE: Make sure to activate virtual environment
```bash
alembic upgrade head
```

3. In case you need to add new migrations.
```bash
alembic revision --autogenerate -m "migration_file_name"
```

# Run project
1. Create .env file inside project directory. Refer to .env.example on what values to keep.

2. Activate virtualenv

3. To run application:
```bash
uvicorn src.main:app --reload --port 8080
```
