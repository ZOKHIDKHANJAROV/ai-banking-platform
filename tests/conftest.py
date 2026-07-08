import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRAUD_SERVICE_ROOT = ROOT / "services" / "fraud-service"

if str(FRAUD_SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(FRAUD_SERVICE_ROOT))

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./test.db"
)
os.environ.setdefault(
    "KAFKA_BOOTSTRAP_SERVERS",
    "localhost:9092"
)
os.environ.setdefault(
    "REDIS_HOST",
    "localhost"
)
os.environ.setdefault(
    "REDIS_PORT",
    "6379"
)
os.environ.setdefault(
    "MLFLOW_TRACKING_URI",
    "http://localhost:5000"
)
