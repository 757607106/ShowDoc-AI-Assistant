/** Enter sends; Shift/Ctrl/Alt+Enter and IME confirmation keep their native behavior. */
export function chatSubmitShortcut(
  event: Pick<KeyboardEvent, 'key' | 'keyCode' | 'isComposing' | 'shiftKey' | 'ctrlKey' | 'altKey' | 'metaKey'>,
): boolean {
  return !event.isComposing && event.keyCode !== 229
    && (event.key === 'Enter' || event.keyCode === 13)
    && !event.shiftKey && !event.ctrlKey && !event.altKey
}
