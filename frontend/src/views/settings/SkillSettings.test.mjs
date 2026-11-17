import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const source = readFileSync(new URL('./SkillSettings.vue', import.meta.url), 'utf8')
test('skills manage source directories and files without installation controls or jobs', () => {
  for (const name of ['listSkillCatalog', 'registerSkillCatalogFromFile', 'registerSkillCatalogFromSource', 'deleteSkillCatalog', 'SkillFilesDrawer']) assert.match(source, new RegExp(name))
  for (const name of ['installSkillCatalog', 'SandboxSkillsPanel', 'listSandboxConfigs', 'useConfigSkillInstallProgress', 'useSkillInstallerModel', 'setInterval', 'setSandboxWorkspacePolicy']) assert.doesNotMatch(source, new RegExp(name))
  assert.match(source, /settings\.skills\.nativeUsage/)
  assert.match(source, /settings\.skills\.addSourceDescription/)
  assert.match(source, /:catalog-id="filesCatalogId"/)
  assert.match(source, /MAX_SKILL_BUNDLE_SIZE_BYTES/)
  assert.match(source, /skillBundleTooManyZipEntries/)
  assert.doesNotMatch(source, /addStepInstall|pickSandboxes|viewInstallProgress|installAccepted|openUpgrade/)
})
