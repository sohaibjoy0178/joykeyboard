"""This avro is the Bengali parser, not Apache Avro's same-name package."""
from PyInstaller.utils.hooks import collect_data_files, copy_metadata

datas = collect_data_files("avro") + copy_metadata("avro-py")
