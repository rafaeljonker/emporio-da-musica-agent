// pt-BR UI copy, verbatim from .design (screens 01-03, voice-and-tone UI copy table).
// Owner decision 2026-11-06: GPU warm-up has one honest stage, "Ligando o modelo".

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
    demoNote: 'Ambiente de demonstração. As credenciais foram enviadas no e-mail da entrega.',
    warmNote: (n: number) => `Ao entrar, o assistente começa a ligar; na primeira vez leva uns ${n} s.`,
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
    localNotice: 'Modo local, sem GPU: cada resposta pode levar de 30 s a alguns minutos.',
  },
  warmup: {
    title: 'Afinando o atendimento',
    checking: 'Verificando o assistente…',
    stagesLabel: 'Etapas',
    stages: {
      server_starting: 'Ligando o modelo',
      model_loading: 'Carregando o modelo',
      ready: 'Pronto pra conversar',
    },
    stageState: { done: 'concluído', current: 'em andamento', pending: 'a seguir' },
    expected: (n: number) => `Normalmente leva cerca de ${n} s.`,
    explain: {
      modal_gpu:
        'O assistente roda no Gemma 4 31B, numa GPU só dele no Modal. Quando ninguém está usando, ela desliga pra não gerar custo, e ligar de novo leva um tempinho.',
      local_cpu: 'O modelo está rodando na sua máquina, sem GPU. Cada resposta pode levar de 30 s a alguns minutos.',
    },
    noteGpu: (firstReply: string) =>
      `Com a máquina já ligada, a primeira mensagem sai em ${firstReply}. Se escrever agora, a mensagem vai sozinha quando ele ficar pronto.`,
    noteLocal:
      'Pra respostas em uns 2 s, use a versão hospedada. Se escrever agora, a mensagem vai sozinha quando ele ficar pronto.',
    network: 'Não consegui falar com o servidor agora. Confere a conexão.',
    longWait: (stage: string) =>
      `Tá demorando mais que o normal. Ainda está em: ${stage}. Pode esperar, a mensagem que você escrever vai assim que ficar pronto.`,
    failed: 'Não consegui ligar o assistente agora. Tenta de novo daqui a pouco.',
    retry: 'Tentar de novo',
    ready: 'Pronto pra conversar.',
    placeholder: 'Pode ir escrevendo',
    queued: 'Vai assim que o assistente ficar pronto',
    undo: 'Desfazer',
    undone: 'Mensagem desfeita. O texto voltou pra caixa de mensagem.',
  },
} as const
