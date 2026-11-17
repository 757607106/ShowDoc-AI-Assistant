"""Preview or repair mapped crawler file directories without reuploading knowledge.

Run from the repository: .venv/bin/python -m scripts.repair_import_directories
--owner-id ID --report downloads/migrations/import-directories.json [--kb-id ID] [--apply]
"""
import argparse
import json
import os
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

from governance.database import connection
from governance.import_directories import repair_documents, repair_plan
from governance.spaces import missing_knowledge_base
from governance.store import Store
from integrations.contextdb import ContextDBError
from webapi.auth import client_for_user


def review_snapshot(client, kb_id):
    items = []
    page = 1
    while True:
        result = client.list_reviews(kb_id, page=page, page_size=100)
        items.extend({key: row.get(key) for key in ('review_id', 'document_id', 'created_at')}
                     for row in result['reviews'])
        if len(items) >= result['total'] or not result['reviews']:
            return sorted(items, key=lambda item: item['review_id'])
        page += 1


def wiki_directories(client, kb_id):
    items, parents = [], [None]
    while parents:
        parent, cursor = parents.pop(), None
        while True:
            result = client.list_wiki_pages(kb_id, parent_page_id=parent, page_type='category', cursor=cursor)
            for row in result['items']:
                items.append({key: row.get(key) for key in ('page_id', 'title', 'parent_page_id', 'sort_order')})
                parents.append(row['page_id'])
            cursor = result.get('next_cursor')
            if not cursor:
                break
    return sorted(items, key=lambda item: item['page_id'])


def document_ids(client, kb_id):
    ids, page = [], 1
    while True:
        rows = client.list_documents(kb_id, page=page, page_size=100)['documents']
        ids.extend(row['id'] for row in rows)
        if len(rows) < 100:
            return sorted(ids)
        page += 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--owner-id', required=True)
    parser.add_argument('--kb-id', action='append')
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    load_dotenv(Path(__file__).resolve().parents[1] / '.env')
    store = Store(owner_id=args.owner_id, client=client_for_user(args.owner_id))
    report = {'started_at': datetime.now(timezone.utc).isoformat(), 'apply': args.apply, 'bases': []}
    args.report.parent.mkdir(parents=True, exist_ok=True)

    def save():
        temporary = args.report.with_suffix('.part')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        os.chmod(temporary, 0o600)
        temporary.replace(args.report)

    if args.kb_id:
        kb_ids = args.kb_id
    else:
        with connection() as conn:
            kb_ids = [row['knowledge_base_id'] for row in conn.execute('''SELECT DISTINCT knowledge_base_id
                FROM knowledge_sync WHERE owner_id=%s AND document_id IS NOT NULL ORDER BY knowledge_base_id''',
                (args.owner_id,)).fetchall()]
    for kb_id in kb_ids:
        entry = {'knowledge_base_id': kb_id}
        report['bases'].append(entry)
        try:
            base = store.client.get_knowledge_base(kb_id)
            entry['name'] = base['name']
            plan, errors = repair_plan(store, kb_id)
            entry.update(plan=plan, planning_errors=errors,
                         groups=dict(Counter(item['directory']['root_name'] for item in plan)))
            print(json.dumps({'base': base['name'], 'planned': len(plan), 'errors': len(errors),
                              'groups': entry['groups']}, ensure_ascii=False), flush=True)
            save()
            if not args.apply:
                continue
            entry['documents_before'] = document_ids(store.client, kb_id)
            entry['reviews_before'] = review_snapshot(store.client, kb_id)
            entry['wiki_directories_before'] = wiki_directories(store.client, kb_id) if base.get('wiki_enabled') else []
            entry['results'] = []
            save()

            def progress(result):
                entry['results'].append(result)
                save()
                if result.get('error') or len(entry['results']) % 20 == 0:
                    print(json.dumps({'base': base['name'], 'processed': len(entry['results']),
                                      'total': len(plan), 'error': result.get('error')}, ensure_ascii=False), flush=True)

            repair_documents(store, kb_id, plan, progress=progress)
            entry['documents_after'] = document_ids(store.client, kb_id)
            entry['reviews_after'] = review_snapshot(store.client, kb_id)
            entry['wiki_directories_after'] = wiki_directories(store.client, kb_id) if base.get('wiki_enabled') else []
            entry['verified'] = {
                'document_ids_preserved': entry['documents_before'] == entry['documents_after'],
                'review_records_preserved': entry['reviews_before'] == entry['reviews_after'],
                'wiki_directories_unchanged': entry['wiki_directories_before'] == entry['wiki_directories_after'],
            }
            if not all(entry['verified'].values()):
                raise RuntimeError('整理前后不变量核对失败，请检查报告')
        except ContextDBError as exc:
            if missing_knowledge_base(exc):
                entry['skipped'] = 'knowledge_base_deleted'
            else:
                entry['error'] = str(exc)
        except Exception as exc:
            entry['error'] = str(exc)
        save()
    report['finished_at'] = datetime.now(timezone.utc).isoformat()
    save()
    failed = any(entry.get('error') or entry.get('planning_errors') or
                 any(result.get('error') for result in entry.get('results', [])) for entry in report['bases'])
    print(json.dumps({'report': str(args.report), 'failed': failed}, ensure_ascii=False), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
