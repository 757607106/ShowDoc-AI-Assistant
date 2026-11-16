"""Recover upload labels without changing stored paths or document identities."""
from pathlib import Path
from uuid import UUID


def upload_name(path, index, original_name=None):
    if isinstance(original_name, str) and original_name:
        return original_name
    path = Path(path)
    if path.parent.parent.name != 'uploads':
        return path.name
    try:
        if str(UUID(path.parent.name)) != path.parent.name.lower():
            return path.name
    except ValueError:
        return path.name
    prefix = f'{index + 1:03d}-'
    return path.name.removeprefix(prefix) or path.name
