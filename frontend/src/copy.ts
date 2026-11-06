// pt-BR UI copy, verbatim from .design (screen-01, screen-03, voice-and-tone UI copy table).

export const copy = {
  login: {
    title: 'Entra aí pra conversar com a Empório',
    tagline: 'A verdade de quem toca.',
    wordmarkAlt: 'Empório da Música',
    email: 'E-mail',
    password: 'Senha',
    submit: 'Entrar',
    submitting: 'Entrando…',
    empty: 'Preenche o e-mail e a senha pra entrar.',
    invalid: 'E-mail ou senha não bateram. Confere e tenta de novo.',
    network: 'Não consegui falar com o servidor agora. Confere a conexão e tenta de novo.',
    // The warm-up sentence ("Ao entrar, o assistente começa a ligar; …{N} s.") lands with
    // GET /api/warm/expected in Task 7.
    demoNote: 'Ambiente de demonstração. As credenciais foram enviadas no e-mail da entrega.',
  },
  chat: {
    title: 'Assistente da Empório',
    subline: 'assistente virtual da loja',
    signOut: 'Sair',
    logLabel: 'Conversa com o assistente da Empório',
    agentPrefix: 'Assistente: ',
    userPrefix: 'Você: ',
    typing: 'O assistente está digitando',
    composerForm: 'Enviar mensagem',
    composerLabel: 'Mensagem',
    composerPlaceholder: 'Escreve sua mensagem',
    send: 'Enviar mensagem',
    errorNoReply: 'Perdi o fio da conversa aqui.',
    errorPartial: 'Perdi o fio no meio da resposta.',
  },
} as const
