from ..common import get_database_path

MOCK_DATA_DIR = get_database_path("mock")
MOCK_DB_PATH = MOCK_DATA_DIR / "db.json"
MOCK_POLICY_PATH = MOCK_DATA_DIR / "policy.md"
MOCK_POLICY_SOLO_PATH = MOCK_DATA_DIR / "policy_solo.md"
MOCK_TASK_SET_PATH = MOCK_DATA_DIR / "tasks.json"