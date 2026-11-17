"""Source directory labels, kept separate from document and task identities."""
import unicodedata


def validate_import_root_name(value):
    if not isinstance(value, str):
        raise ValueError('入库目录名称必须是文本')
    name = value.strip()
    if (not name or len(name) > 200 or name in ('.', '..') or
            any(char in '/\\' or unicodedata.category(char).startswith('C') for char in name)):
        raise ValueError('入库目录名称须为 1～200 个字符，不能包含斜杠、控制字符或仅为 .、..')
    return name


def import_directory(root_name, category='', *, path=None):
    return {'root_name': str(root_name).strip(),
            'path': list(path) if path is not None else [part.strip() for part in category.split('/') if part.strip()]}
