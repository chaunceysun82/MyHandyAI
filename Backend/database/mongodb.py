from typing import Optional

from loguru import logger
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import ConnectionFailure

from config.settings import get_settings

settings = get_settings()


class MongoDB:
    def __init__(self):
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    def initialize(self):
        """Initialize the MongoDB client and database."""
        try:
            uri = settings.MONGODB_URI
            db_name = settings.MONGODB_DATABASE
            
            self._client = MongoClient(uri)
            self._db = self._client.get_database(db_name)
        except ConnectionFailure as e:
            raise RuntimeError(f"Connection Failure: {str(e)}")

        logger.info(f"MongoDB connection initialized. Database: {db_name}")

    def close(self):
        """Close the MongoDB client."""
        if self._client:
            self._client.close()
            logger.info("MongoDB connection closed.")

    def get_database(self) -> Database:
        """Retrieve the database instance."""
        if self._db is None:
            # Auto-initialize if not already done
            self.initialize()
        return self._db

    def get_collection(self, collection_name: str):
        """Retrieve a collection from the database."""
        if self._db is None:
            self.initialize()
        return self._db[collection_name]


mongodb = MongoDB()
