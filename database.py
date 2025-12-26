import json
import time
import os
from sqlalchemy import create_engine, Column, Integer, String, Text, text, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import SQLAlchemyError
import pymongo

# --- Configuration ---
PG_URL = "postgresql://postgres:docker@postgres:5432/operations"
MONGO_URL = "mongodb://mongo:27017/"

# --- PostgreSQL Setup ---
Base = declarative_base()


class Operation(Base):
    __tablename__ = 'operations'

    # We remove autoincrement logic and will handle it manually
    rawid = Column(Integer, primary_key=True, index=True)
    flavor = Column(String)
    operation = Column(String)
    result = Column(Integer)
    arguments = Column(Text)


pg_engine = create_engine(PG_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=pg_engine)

# --- MongoDB Setup ---
mongo_client = pymongo.MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000)
mongo_db = mongo_client["calculator"]
mongo_col = mongo_db["calculator"]


def init_db():
    """Waits for DBs to be ready."""
    print("Initializing Databases...")

    # 1. Wait for Postgres
    pg_ready = False
    for i in range(15):
        try:
            with pg_engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            # We try to create tables, but if they exist (from teacher's image), this skips
            Base.metadata.create_all(bind=pg_engine)
            print("Postgres is ready.")
            pg_ready = True
            break
        except Exception as e:
            print(f"Waiting for Postgres... ({e})")
            time.sleep(2)

    if not pg_ready:
        print("ERROR: Could not connect to Postgres.")

    # 2. Wait for Mongo
    mongo_ready = False
    for i in range(15):
        try:
            mongo_client.admin.command('ping')
            print("Mongo is ready.")
            mongo_ready = True
            break
        except Exception as e:
            print(f"Waiting for Mongo... ({e})")
            time.sleep(2)

    if not mongo_ready:
        print("ERROR: Could not connect to Mongo.")


def save_operation(flavor: str, operation: str, result: int, arguments: list):
    """
    Manually generates ID, saves to Postgres, then saves to Mongo.
    """
    if arguments is None:
        arguments = []

    try:
        args_str = json.dumps(arguments)
    except Exception:
        args_str = "[]"

    db = SessionLocal()
    generated_id = None

    try:
        # --- MANUAL ID GENERATION ---
        # 1. Find the current maximum rawid in the table
        max_id = db.query(func.max(Operation.rawid)).scalar()

        # 2. If table is empty, start at 1. Otherwise, increment by 1.
        next_id = 1 if max_id is None else max_id + 1

        # 3. Create object with EXPLICIT id
        new_op = Operation(
            rawid=next_id,
            flavor=flavor,
            operation=operation,
            result=result,
            arguments=args_str
        )

        db.add(new_op)
        db.commit()
        db.refresh(new_op)
        generated_id = new_op.rawid

    except Exception as e:
        print(f"Error saving to Postgres: {e}")
        db.rollback()
        db.close()
        return
    finally:
        db.close()

    # 2. Save to Mongo (Using the same ID)
    if generated_id:
        doc = {
            "rawid": generated_id,
            "flavor": flavor,
            "operation": operation,
            "result": result,
            "arguments": args_str
        }
        try:
            mongo_col.insert_one(doc)
        except Exception as e:
            print(f"Error saving to Mongo: {e}")


def get_history_from_db(persistence_method: str, flavor: str = None):
    results = []

    if persistence_method == "POSTGRES":
        db = SessionLocal()
        try:
            query = db.query(Operation)
            if flavor:
                query = query.filter(Operation.flavor == flavor)

            rows = query.all()
            for row in rows:
                results.append({
                    "id": row.rawid,
                    "flavor": row.flavor,
                    "operation": row.operation,
                    "result": row.result,
                    "arguments": json.loads(row.arguments)
                })
        except Exception as e:
            print(f"Error reading Postgres: {e}")
        finally:
            db.close()

    elif persistence_method == "MONGO":
        query = {}
        if flavor:
            query["flavor"] = flavor

        try:
            cursor = mongo_col.find(query, {"_id": 0})
            for doc in cursor:
                results.append({
                    "id": doc.get("rawid"),
                    "flavor": doc.get("flavor"),
                    "operation": doc.get("operation"),
                    "result": doc.get("result"),
                    "arguments": json.loads(doc.get("arguments", "[]"))
                })
        except Exception as e:
            print(f"Error reading Mongo: {e}")

    return results