import pyarrow
import pyarrow.parquet as pq

from sciety_labs.utils.cache import DiskSingleObjectCache


class ArrowTableDiskSingleObjectCache(DiskSingleObjectCache[pyarrow.Table]):
    compression: str = 'GZIP'
    memory_map: bool = True

    def serialize_to_file(self, obj: pyarrow.Table, file_path: str):
        pq.write_table(obj, file_path, compression=self.compression)

    def deserialize_from_file(self, file_path: str) -> pyarrow.Table:
        return pq.read_table(file_path, memory_map=self.memory_map)
