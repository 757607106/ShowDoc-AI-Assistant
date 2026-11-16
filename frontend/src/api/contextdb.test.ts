import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const script = ts.transpileModule(readFileSync(new URL('./contextdb.ts', import.meta.url), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
const plain = (value: any) => JSON.parse(JSON.stringify(value))
function fixture(handler: (method: string, path: string, body: any, config?: any) => any = () => ({ data: {} })) {
  const calls: any[] = [], api: any = {}
  const request = Object.fromEntries(['get','post','put','patch','del','getDown','postUpload'].map(method=>[method,async(path:string,body:any,config:any,uploadConfig:any)=>{
    calls.push({method,path,body,config:uploadConfig || config})
    return handler(method,path,body,uploadConfig || config)
  }]))
  runInNewContext(script,{exports:api,FormData,Blob,File,URLSearchParams,require:()=>request})
  return {api,calls}
}
test('official names and real identities win over historical display aliases',()=>{
  const {api}=fixture()
  const kb=api.kbView({id:'kb',name:'官方业务名',display_name:'旧别名',original_name:'旧机器名',wiki_enabled:false,graph_enabled:true})
  assert.equal(kb.name,'官方业务名');assert.equal(kb.original_name,'官方业务名');assert.equal(kb.id,'kb')
  assert.equal(kb.capabilities.graph,true);assert.equal(kb.capabilities.vector,true)
})
test('each mode and review option creates exactly one official knowledge base',async()=>{
  for(const mode of ['source','graph','wiki'])for(const review of [false,true]){
    const f=fixture(()=>({data:{id:'new'}}))
    await f.api.createBase({name:'业务库',review_enabled:review,indexing_strategy:{wiki_enabled:mode==='wiki',graph_enabled:mode==='graph'}})
    assert.equal(f.calls.length,1)
    assert.equal(f.calls[0].path,'/api/contextdb/v1/knowledge/knowledge_bases')
    assert.deepEqual(plain(f.calls[0].body),{name:'业务库',wiki_enabled:mode==='wiki',graph_enabled:mode==='graph',review_enabled:review})
  }
  const f=fixture();await assert.rejects(f.api.createBase({name:'bad',indexing_strategy:{wiki_enabled:true,graph_enabled:true}}),/一种/)
  assert.equal(f.calls.length,0)
})
test('rename and review updates keep the ID and never forward a mode change or touch business aliases',async()=>{
  const f=fixture((_method,_path,body)=>({data:{id:'kb',lifecycle:'deleted',...body}}))
  await f.api.updateBase('kb',{name:'改后',review_enabled:false,indexing_strategy:{wiki_enabled:false,graph_enabled:true}})
  assert.deepEqual(plain(f.calls[0].body),{knowledge_base_id:'kb',name:'改后',review_enabled:false})
  await f.api.deleteBase('kb /?')
  assert.equal(f.calls[1].method,'del');assert.match(f.calls[1].path,/knowledge_base_id=kb%20%2F%3F$/)
  assert.equal(f.calls.length,2)
})
test('document mutations use declared native contracts and preserve metadata values',async()=>{
  const f=fixture()
  await f.api.deleteDocuments('kb',['doc-a','doc-b'])
  await f.api.retryDocument('doc-a')
  await f.api.updateDocumentMetadata('doc-a',{title:'new',count:3})
  assert.deepEqual(plain(f.calls.map(({method,path,body})=>({method,path,body}))),[
    {method:'del',path:'/api/contextdb/v1/knowledge/documents/batch',body:{knowledge_base_id:'kb',ids:['doc-a','doc-b']}},
    {method:'post',path:'/api/contextdb/v1/knowledge/documents/retry',body:{document_id:'doc-a'}},
    {method:'put',path:'/api/contextdb/v1/knowledge/documents/metadata',body:{document_id:'doc-a',metadata:{title:'new',count:3}}},
  ])
})
test('permissions require both the local role and authoritative effective permission',()=>{
  const {api}=fixture(), kb={id:'a'}
  const profile=(permission:string,mode='advanced')=>({mode,evaluation_state:'active',member:{role:'member',status:'active'},knowledge_base_permissions:[{knowledge_base_id:'a',current_permission:permission}]})
  assert.deepEqual(plain(api.knowledgeAccess(kb,null,true)),{write:false,manage:false,delete:false})
  assert.deepEqual(plain(api.knowledgeAccess(kb,profile('read'),true)),{write:false,manage:false,delete:false})
  assert.deepEqual(plain(api.knowledgeAccess(kb,profile('write'),true)),{write:true,manage:false,delete:false})
  assert.deepEqual(plain(api.knowledgeAccess(kb,profile('kb_manage'),true)),{write:true,manage:true,delete:false})
  assert.deepEqual(plain(api.knowledgeAccess(kb,profile('all'),true)),{write:true,manage:false,delete:false})
  assert.deepEqual(plain(api.knowledgeAccess(kb,profile('all','personal_compatibility'),true)),{write:true,manage:true,delete:true})
  assert.equal(api.knowledgeAccess(kb,profile('kb_manage'),false).write,false)
  assert.equal(api.knowledgeAccess(kb,{...profile('all'),evaluation_state:'disabled'},true).write,false)
  assert.equal(api.knowledgeAccess(kb,{member:{role:'owner',status:'disabled'}},true).manage,false)
})
test('permission pagination retains later library grants',async()=>{
  const f=fixture((_m,_p,body)=>({data:{member:{role:'member'},total:101,knowledge_base_permissions:body.params.page===1?Array.from({length:100},(_,i)=>({knowledge_base_id:String(i),current_permission:'read'})):[{knowledge_base_id:'last',current_permission:'write'}]}}))
  const result=await f.api.getBasePermissions()
  assert.equal(result.knowledge_base_permissions.length,101);assert.equal(result.knowledge_base_permissions[100].knowledge_base_id,'last')
})
test('small file replacement sends multipart PUT with the original document identity',async()=>{
  const f=fixture(),file=new File(['new'],'replacement.md',{type:'text/markdown'})
  await f.api.replaceDocumentFile('doc',file)
  assert.equal(f.calls[0].method,'put');assert.equal(f.calls[0].body.get('document_id'),'doc')
  assert.equal(f.calls[0].body.get('name'),null);assert.equal(f.calls[0].body.get('file').name,'replacement.md')
})
const largeFile={name:'large.pdf',type:'application/pdf',size:101*1024*1024,slice:()=>new Blob(['part'])} as File
test('large replacements send verified sequential parts and complete the official upload',async()=>{
  const f=fixture((_m,path,body)=>{
    if(path.endsWith('/init-upload'))return {data:{upload_ticket:'ticket',chunk_size:100*1024*1024}}
    if(path.endsWith('/chunks'))return {data:{part_number:Number(body.get('part_number')),etag:'etag'+body.get('part_number')}}
    return {data:{id:'new-document-id'}}
  })
  await f.api.replaceDocumentFile('doc',largeFile)
  assert.deepEqual(f.calls.map(item=>item.path.split('/').pop()),['init-upload','chunks','chunks','complete'])
  assert.deepEqual(plain(f.calls[3].body),{parts:[{part_number:1,etag:'etag1'},{part_number:2,etag:'etag2'}]})
  assert.equal(f.calls[1].config.headers['X-Upload-Ticket'],'ticket')
})
test('failed part is aborted while uncertain completion is never aborted or retried',async()=>{
  for(const phase of ['chunks','complete']){
    const f=fixture((_m,path,body)=>{
      if(path.endsWith('/init-upload'))return {data:{upload_ticket:'ticket',chunk_size:200*1024*1024}}
      if(path.endsWith('/'+phase))throw new Error('network uncertain')
      return {data:{part_number:Number(body?.get?.('part_number')),etag:'etag'}}
    })
    await assert.rejects(f.api.replaceDocumentFile('doc',largeFile),/uncertain/)
    assert.equal(f.calls.some(call=>call.path.endsWith('/abort')),phase==='chunks')
    assert.equal(f.calls.filter(call=>call.path.endsWith('/complete')).length,phase==='complete'?1:0)
  }
})

test('unconfirmed deletion never becomes a completed library deletion',async()=>{
 const f=fixture(()=>({data:{lifecycle:'deleting'}}))
 await assert.rejects(f.api.deleteBase('kb'),/尚未确认/)
 assert.equal(f.calls.length,1)
})
test('new large-file uploads use POST init with only the exact target library',async()=>{
 const f=fixture((_method,path,body)=>{
  if(path.endsWith('/init-upload'))return {data:{upload_ticket:'ticket',chunk_size:200*1024*1024}}
  if(path.endsWith('/chunks'))return {data:{part_number:1,etag:'etag'}}
  return {data:{id:'created'}}
 })
 await f.api.uploadDocumentFile('kb-only',largeFile)
 assert.equal(f.calls[0].method,'post')
 assert.deepEqual(plain(f.calls[0].body),{knowledge_base_id:'kb-only',file_name:'large.pdf',mime_type:'application/pdf'})
})

test('knowledge-base list reads the complete official result once without invented pagination',async()=>{
 const bases=Array.from({length:101},(_,id)=>({id:String(id),name:id===100?'_governance':'库'+id}))
 const f=fixture(()=>({data:{knowledge_bases:bases}}));const result=await f.api.listBases()
 assert.equal(f.calls.length,1);assert.equal(f.calls[0].body.params,undefined);assert.equal(result.data.length,101);assert.equal(result.data[100].name,'_governance')
})
test('ordinary uploads preserve the chosen directory and per-upload review override',async()=>{
 const f=fixture();await f.api.uploadDocumentFile('kb',new File(['text'],'source.md'),{parent_node_id:'folder',review_enabled:false})
 assert.equal(f.calls[0].body.get('knowledge_base_id'),'kb');assert.equal(f.calls[0].body.get('parent_node_id'),'folder');assert.equal(f.calls[0].body.get('review_enabled'),'false')
 await assert.rejects(f.api.uploadDocumentFile('kb',largeFile,{review_enabled:true}),/分片上传/)
 assert.equal(f.calls.length,1)
})
