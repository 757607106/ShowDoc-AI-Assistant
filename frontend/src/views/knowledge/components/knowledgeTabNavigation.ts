export function navigateKnowledgeTabs(event: KeyboardEvent) {
  if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return
  const tabs = Array.from((event.currentTarget as HTMLElement).querySelectorAll<HTMLButtonElement>('[role="tab"]:not(:disabled)'))
  const index = tabs.indexOf(event.target as HTMLButtonElement)
  if (index === -1) return
  event.preventDefault()
  const step = event.key === 'ArrowRight' ? 1 : -1
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + step + tabs.length) % tabs.length
  if (next === index) return
  tabs[next]?.focus()
  tabs[next]?.click()
}
