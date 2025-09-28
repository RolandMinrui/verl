from ..common import get_database_path

RETAIL_DATA_DIR = get_database_path("retail")
RETAIL_DB_PATH = RETAIL_DATA_DIR / "db.json"
RETAIL_POLICY_PATH = RETAIL_DATA_DIR / "policy.md"
RETAIL_TASK_SET_PATH = RETAIL_DATA_DIR / "tasks.json"