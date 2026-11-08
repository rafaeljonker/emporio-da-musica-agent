/** Send needs text and no reply in flight. */
export const canSend = (busy: boolean, text: string) => !busy && text.trim() !== ''

/** "Perguntar ao assistente" never discards a draft: the question goes on a new line after it. */
export const appendQuestion = (draft: string, question: string) =>
  draft.trim() ? `${draft.trimEnd()}\n${question}` : question
