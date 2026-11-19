import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import vm from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('./Input-field.vue', import.meta.url), 'utf8')
const focusCode = source.slice(source.indexOf('const focusInput ='), source.indexOf('const onInput ='))
const sendCode = source.slice(source.indexOf('const createSession ='), source.indexOf('const updateAgentModeDropdownPosition ='))

test('only the owning conversation can save its draft on teardown', () => {
  const code = source.slice(source.indexOf('onBeforeUnmount(() =>'), source.indexOf('onUnmounted(() =>'))
  for (const [key, account, workspace, shouldSave] of [
    ['session-a', 'owner', 1, true],
    ['session-a', 'other-account', 1, false],
    ['session-a', 'owner', 2, false],
    ['', 'owner', 1, false],
  ]) {
    const stored = [], revoked = []
    let teardown
    vm.runInNewContext(code, {
      onBeforeUnmount: fn => { teardown = fn }, replaceDraftDialog: undefined,
      draftKey: key, draftUser: 'owner', draftTenant: 1,
      mentionAuth: { currentUserId: account, effectiveTenantId: workspace },
      query: { value: '未发送的问题' },
      uploadedImages: { value: [{ file: 'image', preview: 'blob:image' }] },
      uploadedAttachments: { value: [{ id: 'attachment-a' }] },
      suggestionOriginFor: () => undefined,
      saveChatDraft: (...args) => stored.push(args),
      URL: { revokeObjectURL: value => revoked.push(value) },
      getTextareaEl: () => null,
    })
    teardown()
    assert.equal(stored.length, shouldSave ? 1 : 0)
    if (shouldSave) {
      assert.equal(stored[0][0], key)
      assert.equal(stored[0][1].text, '未发送的问题')
      assert.equal(stored[0][1].images[0], 'image')
      assert.equal(stored[0][1].attachments[0].id, 'attachment-a')
    }
    assert.deepEqual(revoked, ['blob:image'])
  }
})

for (const mode of ['normal', 'embedded', 'new']) {
  test(`${mode} send restores focus and keeps the draft only during new session creation`, async () => {
    const effects = [], ticks = []
    let sentModel
    const textarea = {
      isConnected: true,
      focus: options => effects.push(['focus', options.preventScroll]),
      blur: () => { throw new Error('sending must not blur the textarea') },
    }
    const context = {
      props: { isReplying: false, embeddedMode: mode === 'embedded', sessionId: mode === 'normal' ? 'existing' : undefined },
      uploadedAttachments: { value: [] }, uploadedImages: { value: [] },
      allSelectedItems: { value: [] }, selectedModelId: { value: 'model' },
      composerModelId: { value: 'host-model' },
      selectedAgent: { value: { config: {} } },
      settingsStore: {}, chatResources: { isLoaded: () => true },
      collectAgentNotReadyReasons: () => ({ keys: [], labels: [] }),
      attachmentUploadRef: { value: null },
      emit: (name, _query, model) => {
        effects.push([name])
        if (name === 'send-msg') sentModel = model
      },
      clearvalue: () => effects.push(['clear']),
      clearDraft: () => effects.push(['clear']),
      suggestionOriginFor: () => undefined,
      getTextareaEl: () => textarea,
      nextTick: () => new Promise(resolve => ticks.push(resolve)),
    }
    const send = vm.runInNewContext(ts.transpile(`${focusCode}\n${sendCode}\ncreateSession`), context)
    await send('hello')
    assert.deepEqual(effects, mode === 'new' ? [['send-msg']] : [['send-msg'], ['clear']])
    // Embedded, the host's model goes out, never the main chat's pick.
    if (mode === 'embedded') assert.equal(sentModel, 'host-model')
    if (mode !== 'embedded') assert.equal(sentModel, 'model')
    for (const resolve of ticks) resolve()
    await new Promise(setImmediate)
    assert.deepEqual(effects.at(-1), ['focus', true])
  })
}

test('failed sends restore text, images and attachments without overwriting a newer draft', () => {
  const code = source.slice(source.indexOf('const restoreDraft ='), source.indexOf('</script>'))
  let exposed
  const query = { value: '' }, uploadedImages = { value: [] }, uploadedAttachments = { value: [] }
  const restoredAttachments = []
  const image = { name: 'evidence.png' }, attachment = { id: 'attachment-a' }
  vm.runInNewContext(ts.transpile(code), {
    query, uploadedImages, uploadedAttachments, suggestedDraft: {},
    clearDraft() {},
    attachmentUploadRef: { value: { restore: files => {
      restoredAttachments.push(files)
      uploadedAttachments.value = files
    } } },
    URL: { createObjectURL: file => `blob:${file.name}` },
    defineExpose: api => { exposed = api },
    focusInput() {},
  })
  exposed.restoreDraft('original question', [image], [attachment])
  assert.equal(query.value, 'original question')
  assert.equal(uploadedImages.value[0].file, image)
  assert.equal(uploadedImages.value[0].preview, 'blob:evidence.png')
  assert.equal(uploadedAttachments.value[0], attachment)
  assert.equal(restoredAttachments[0][0], attachment)
  exposed.restoreDraft('must not replace this')
  assert.equal(query.value, 'original question')
  assert.equal(restoredAttachments.length, 1)
  query.value = ''
  uploadedImages.value = []
  uploadedAttachments.value = [{ id: 'newer-attachment' }]
  exposed.restoreDraft('older request', [], [attachment])
  assert.equal(query.value, '')
  assert.equal(uploadedAttachments.value[0].id, 'newer-attachment')
  assert.equal(restoredAttachments.length, 1)
})

test('attachment restore resumes polling or retries an unfinished upload for the same session', () => {
  const uploadSource = readFileSync(new URL('./AttachmentUpload.vue', import.meta.url), 'utf8')
  const code = uploadSource.slice(uploadSource.indexOf('defineExpose({'), uploadSource.indexOf('</script>'))
  const attachments = { value: [] }, emitted = [], polls = [], uploads = []
  let exposed
  vm.runInNewContext(ts.transpile(code), {
    attachments, props: { sessionId: 'session-a' },
    triggerFileSelect() {}, addFiles() {},
    uploadAttachment: attachment => uploads.push(attachment),
    emitFiles: () => emitted.push(attachments.value),
    scheduleStatusPoll: attachment => polls.push(attachment),
    defineExpose: api => { exposed = api },
  })
  const pending = { documentId: 'pending', status: 'processing' }, ready = { documentId: 'ready', status: 'ready' }
  const uploading = { id: 'uploading', status: 'uploading' }
  exposed.restore([pending, ready, uploading])
  assert.equal(attachments.value.length, 3)
  assert.equal(emitted.length, 1)
  assert.equal(polls[0].documentId, pending.documentId)
  assert.equal(polls.length, 1)
  assert.equal(uploads[0].id, uploading.id)
  assert.notEqual(uploads[0], uploading)
})

test('a queued focus does not focus a textarea removed during navigation', async () => {
  let resolveTick, connected = true, focused = false
  const focus = vm.runInNewContext(`${focusCode}\nfocusInput`, {
    nextTick: () => new Promise(resolve => { resolveTick = resolve }),
    getTextareaEl: () => ({ isConnected: connected, focus: () => { focused = true } }),
  })
  const pending = focus()
  connected = false
  resolveTick()
  await pending
  assert.equal(focused, false)
})

for (const embeddedMode of [false, true]) {
  test(`${embeddedMode ? 'embedded' : 'main'} send respects the composer's resource scope`, async () => {
    const selected = [
      { id: 'main-kb', name: 'Main KB', type: 'kb' },
      { id: 'main-file', name: 'Main file', type: 'file', kbId: 'main-kb' },
      { id: 'main-tag', name: 'Main tag', type: 'tag', kbId: 'main-kb' },
      { id: 'main-mcp', name: 'Main MCP', type: 'mcp' },
      { id: 'main-skill', name: 'Main skill', type: 'skill', skillName: 'main-skill' },
    ]
    let emitted
    const send = vm.runInNewContext(ts.transpile(`${sendCode}\ncreateSession`), {
      props: { embeddedMode, isReplying: false },
      uploadedAttachments: { value: [] }, uploadedImages: { value: [] },
      allSelectedItems: { value: selected },
      selectedModelId: { value: 'main-model' }, composerModelId: { value: 'host-model' },
      selectedAgent: { value: { config: {} } },
      settingsStore: {}, chatResources: { isLoaded: () => true },
      collectAgentNotReadyReasons: () => ({ keys: [], labels: [] }),
      attachmentUploadRef: { value: null },
      emit: (...args) => { emitted = args },
      clearvalue() {}, clearDraft() {}, focusInput: async () => {}, suggestionOriginFor: () => undefined,
    })
    await send('continue')
    const [event, query, model, mentions] = emitted
    assert.equal(event, 'send-msg')
    assert.equal(query, 'continue')
    assert.equal(model, embeddedMode ? 'host-model' : 'main-model')
    assert.deepEqual(Array.from(mentions, item => item.id), embeddedMode ? [] : selected.map(item => item.id))
    assert.equal(selected.length, 5, 'sending must not clear the main composer selection')
  })
}

test('teardown blurs the active textarea before it is detached', () => {
  const code = source.slice(source.indexOf('onBeforeUnmount(() =>'), source.indexOf('onUnmounted(() =>'))
  let teardown, blurred = false
  const textarea = { isConnected: true, blur: () => { blurred = true } }
  vm.runInNewContext(code, {
    onBeforeUnmount: fn => { teardown = fn }, getTextareaEl: () => textarea,
    document: { activeElement: textarea }, draftKey: '', uploadedImages: { value: [] }, replaceDraftDialog: undefined,
  })
  teardown()
  assert.equal(blurred, true)
})

test('new-session focus survives consumption of the first query and runs on child mount', () => {
  const page = readFileSync(new URL('../views/chat/index.vue', import.meta.url), 'utf8')
  const snapshot = page.match(/const focusComposerOnMount = [^;]+;/)[0]
  const firstQuery = { value: 'initial question' }
  const autoFocus = vm.runInNewContext(`${snapshot}\nfirstQuery.value = ''; focusComposerOnMount`, {
    firstQuery, props: { embeddedMode: false, initialQuery: '' },
  })
  assert.equal(autoFocus, true)
  // An embedded host passes its own first message; the main chat's draft is not its.
  const embedded = { embeddedMode: true, initialQuery: 'host question' }
  assert.equal(vm.runInNewContext(`${snapshot}\nfocusComposerOnMount`, { firstQuery, props: embedded }), true)
  assert.equal(vm.runInNewContext(`${snapshot}\nfocusComposerOnMount`, {
    firstQuery: { value: 'main draft' }, props: { embeddedMode: true, initialQuery: '' },
  }), false)
  assert.match(page, /:auto-focus="focusComposerOnMount"/)
  const mountStart = source.slice(source.indexOf('onMounted(() => {'), source.indexOf('// 嵌入时 agent/KB 由宿主注入，只需'))
  let mounted, focused = false
  vm.runInNewContext(`${mountStart}\n});`, {
    props: { autoFocus }, onMounted: fn => { mounted = fn }, focusInput: () => { focused = true },
  })
  assert.equal(focused, false)
  mounted()
  assert.equal(focused, true)
})
