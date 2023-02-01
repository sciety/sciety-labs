import os.path


SQL_DIR = os.path.dirname(__file__)


def get_sql_path(sql_filename: str) -> str:
    return os.path.join(SQL_DIR, sql_filename)
