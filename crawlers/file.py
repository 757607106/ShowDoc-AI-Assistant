"""Import files from the controlled upload directory as immutable task sources."""
import hashlib
import os
import shutil
from pathlib import Path

from common.converter import clean_filename
from .base import BaseCrawler, CrawledDocument, DocumentStub


class FileCrawler(BaseCrawler):
    platform = "file"
    display_name = "上传文件"
    requires_auth = False

    def __init__(self, save_dir, file_paths, progress_callback=None):
        super().__init__(save_dir, progress_callback)
        upload_root = (Path(os.getenv("GOVERNANCE_DATA_DIR", Path(__file__).resolve().parents[1] / "downloads")) / "uploads").resolve()
        self.files = {}
        for value in file_paths:
            path = Path(value).resolve()
            if not path.is_relative_to(upload_root) or not path.is_file():
                raise ValueError("文件必须位于平台上传目录中")
            digest = hashlib.sha256(path.name.encode() + b'\0')
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            key = digest.hexdigest()[:24]
            self.files[key] = path

    def list_documents(self):
        return [DocumentStub(key, path.stem, "上传文件") for key, path in self.files.items()]

    def fetch_document(self, stub):
        original = self.files[stub.id]
        relative = Path("sources") / f"{stub.id}_{clean_filename(original.name)}"
        destination = Path(self.save_dir) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        return CrawledDocument(stub.id, stub.title, stub.category, "", "",
                               {"filename": original.name}, "file", source_path=str(relative))
