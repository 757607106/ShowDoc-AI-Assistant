import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SkillSettings.vue', import.meta.url), 'utf8')

test('skill catalog cards expose files and deletion with stable catalog identity', () => {
  assert.match(source, /v-for="item in filteredCatalog" :key="item.id"/)
  assert.match(source, /@click="openCatalogFiles\(item\)"/)
  assert.match(source, /@click="askDelete\(item\)"/)
  assert.match(source, /<SkillFilesDrawer[^>]*:catalog-id="filesCatalogId"/)
  assert.doesNotMatch(source, /installSkillCatalog|reinstallConfigSkill|useConfigSkillInstallProgress/)
})

test('one registration drawer accepts files or source URLs and disables duplicate submits', () => {
  assert.match(source, /:confirm-loading="addBusy" :confirm-disabled="addPrimaryDisabled"/)
  assert.match(source, /@confirm="registerCatalog"/)
  assert.match(source, /type="file" accept="\.zip,\.md"/)
  assert.match(source, /v-model="sourceInput" :disabled="addBusy \|\| Boolean\(pendingFile\)"/)
  assert.match(source, /v-if="addBusy && pendingFile" :percentage="uploadPercent"/)
  assert.doesNotMatch(source, /addStep|installerModel|sandbox-pick/)
})
