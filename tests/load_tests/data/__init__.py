import os.path


DATA_DIR = os.path.dirname(__file__)


def get_data_file_path(filename: str) -> str:
    return os.path.join(DATA_DIR, filename)
