"""Import files from the controlled upload directory as immutable task sources."""
import hashlib
import os
import shutil
from pathlib import Path

from common.converter import clean_filename
from common.upload_names import upload_name
from .base import BaseCrawler, CrawledDocument, DocumentStub


class FileCrawler(BaseCrawler):
    platform = "file"
    display_name = "上传文件"
    requires_auth = False
    root_categories = ('上传文件',)

    def __init__(self, save_dir, file_paths, progress_callback=None, file_names=None):
        super().__init__(save_dir, progress_callback)
        if file_names is not None and len(file_names) != len(file_paths):
            raise ValueError("上传文件路径与名称数量不一致")
        upload_root = (Path(os.getenv("GOVERNANCE_DATA_DIR", Path(__file__).resolve().parents[1] / "downloads")) / "uploads").resolve()
        self.files = {}
        self.file_names = {}
        for index, value in enumerate(file_paths):
            path = Path(value).resolve()
            if not path.is_relative_to(upload_root) or not path.is_file():
                raise ValueError("文件必须位于平台上传目录中")
            digest = hashlib.sha256(path.name.encode() + b'\0')
            with path.open('rb') as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(chunk)
            key = digest.hexdigest()[:24]
            self.files[key] = path
            self.file_names[key] = upload_name(path, index, file_names[index] if file_names is not None else None)

    def list_documents(self):
        return [DocumentStub(key, Path(self.file_names[key]).stem, "上传文件") for key in self.files]

    def fetch_document(self, stub):
        original = self.files[stub.id]
        relative = Path("sources") / f"{stub.id}_{clean_filename(original.name)}"
        destination = Path(self.save_dir) / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original, destination)
        return CrawledDocument(stub.id, stub.title, stub.category, "", "",
                               {"filename": self.file_names[stub.id]}, "file", source_path=str(relative))
