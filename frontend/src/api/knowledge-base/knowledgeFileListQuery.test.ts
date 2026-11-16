import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';

import { buildListKnowledgeFilesQuery } from './knowledgeFileListQuery';

test('知识文件列表请求会传递排序字段和方向', () => {
  const query = new URLSearchParams(buildListKnowledgeFilesQuery({
    page: 2,
    page_size: 35,
    sort_by: 'file_name',
    sort_order: 'asc',
    folder_path: '',
  }));

  assert.equal(query.get('page'), '2');
  assert.equal(query.get('page_size'), '35');
  assert.equal(query.get('sort_by'), 'file_name');
  assert.equal(query.get('sort_order'), 'asc');
  assert.equal(query.get('folder_path'), '');
});

test('ContextDB document browsing keeps root folder UI parameters on the official document transport', async () => {
  const source = readFileSync(new URL('./index.ts', import.meta.url), 'utf8');
  const start = source.indexOf('export function listKnowledgeFiles(');
  const end = source.indexOf('/** One node', start);
  const script = ts.transpileModule(source.slice(start, end).replace('export ', '') + '\nreturn listKnowledgeFiles', {}).outputText;
  const calls: any[] = [];
  const native = { listDocuments: async (id: string, params: any) => { calls.push([id, params]); return { data: [{ file_name: '原始文件.md' }], total: 1 }; } };
  const legacy = (...args: any[]) => { calls.push(args); return 'legacy'; };
  const query = { page: 1, page_size: 35, folder_path: '', folder_recursive: false };
  const list = new Function('IS_CONTEXTDB', 'contextdb', 'get', 'withKnowledgeReadContext', script)(true, native, legacy, (path: string) => path);
  assert.equal((await list('kb-id', query)).data[0].file_name, '原始文件.md');
  assert.deepEqual(calls, [['kb-id', query]]);
  calls.length = 0;
  const oldList = new Function('IS_CONTEXTDB', 'contextdb', 'get', 'withKnowledgeReadContext', script)(false, native, legacy, (path: string) => path);
  assert.equal(oldList('kb-id', query), 'legacy');
  assert.equal(calls[0][0], '/api/v1/knowledge-bases/kb-id/knowledge');
});
