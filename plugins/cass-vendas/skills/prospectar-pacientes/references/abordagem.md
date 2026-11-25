# Como escrever a primeira mensagem

Abra este arquivo antes de escrever qualquer mensagem da rodada. O método é Social Selling aplicado a nutricionista que aborda paciente pelo Direct: ativação sem oferta, condução com perguntas fáceis, conversão só depois que a pessoa conta o que quer.

## Ordem de envio (do mais quente para o mais frio)

1. Comentou num post seu.
2. Curtiu um post seu.
3. Comentou num post de concorrente.
4. Curtiu um post de concorrente.

Dentro de cada grupo, vale a nota do script. O `coletar` já entrega os leads nesta ordem. A ordem é uma régua de prioridade, não prova de que a pessoa quer comprar: curtida e comentário são só um rastro de interesse.

## Antes de escrever: leia a bio

Profissional de outra área (dentista, médica, advogada, professora) é paciente em potencial: fica, mesmo com "consultório" ou "clínica" na bio. Conta verificada ou com mais de 100 mil seguidores também fica se for pessoa. Tire da rodada (`marcar @perfil --status descartado --obs "motivo"`):

- quem vende na mesma área: nutricionista, personal, treinador, estética, suplemento, comida saudável;
- marca, loja, clínica ou perfil de empresa sem pessoa por trás;
- quem parece menor de idade;
- quem fala de transtorno alimentar, luto ou doença grave na bio (abordagem comercial ali é desrespeito);
- (sem marcar) quem não tem na bio nem nos dados nenhum fato concreto para o relacionamento: deixe fora desta lista e não invente um fato. Ela continua disponível para outra rodada.

Perfil fechado entra na lista: a bio aparece, os posts não. Tire o fato do relacionamento só da bio.

## Os 4 elementos

Toda primeira mensagem tem as quatro partes, nesta ordem. Cada parte vira uma linha no Direct.

| Parte | O que é | Exemplo |
|---|---|---|
| 1. Nome + hora do dia | Primeiro nome e a saudação do horário de Brasília (bom dia até 12h, boa tarde até 18h, boa noite depois) | "Oi, Carol, boa tarde!" |
| 2. O motivo | Por que você está chamando agora | "Vi que vc comentou na minha receita de panqueca proteica" |
| 3. O relacionamento | Um fato concreto do perfil da pessoa e, se couber, uma pergunta leve sobre esse fato | "Vi tb que vc corre, tá treinando pra alguma prova?" |
| 4. O dia + o tchau | Fecho leve com o dia da semana, sem cobrar resposta | "Se precisar de algo, conta comigo. Uma boa terça pra vc!" |

### O motivo depende da origem

- **Interagiu no seu perfil:** diga o que ela fez e em qual post. "Vi que vc curtiu meu post sobre café da manhã". Comentou: cite o tema do post, não repita o comentário inteiro.
- **Veio de concorrente:** o motivo sai do perfil dela. Nunca diga onde você a achou e nunca cite o concorrente nem o comentário que ela fez lá. Ela não te conhece, então diga quem você é numa frase curta, sem oferta: "Sou a Ana, nutri aqui do Insta, e vi que vc faz CrossFit 5x na semana".
- O comentário que ela fez (inclusive uma dor, como "preciso muito disso" num post sobre compulsão) serve para você entender a pessoa. Não entra na primeira mensagem.

### A pergunta

- Uma pergunta só, curta, que se responde sem pensar.
- Só sobre o fato do perfil: prova, esporte, profissão, cidade, filho. "Faz tempo que vc corre?"
- Nunca sobre hábito, alimentação, corpo, peso ou dificuldade. Isso vem depois que ela responder.
- Perfil sem gancho para pergunta: mande sem pergunta.

## Régua de escrita

Confira cada mensagem contra esta lista antes de entregar. O script recusa a mensagem que falhar nos itens mecânicos.

- Até umas 45 palavras. Registro de Direct: "vc", "tá", "tb" (ou o jeito dela, ver o último item).
- No máximo 1 emoji. Sem travessão, sem negrito, sem link.
- Sem oferta: nada de consulta, atendimento, agenda, acompanhamento, plano alimentar, desconto, "te mando umas receitas".
- Não diga o que a pessoa sente ou vive ("imagino que a rotina seja corrida", "sei como é difícil").
- Não peça desculpa pelo contato ("desculpa o incômodo", "sem compromisso").
- Sem "não é X, é Y". Afirme direto.
- Sem comentário sobre corpo, peso ou aparência.
- **Teste da troca:** se a frase serviria igual para outra pessoa, troque por algo do perfil dela.
- Nenhuma mensagem igual à outra. Texto repetido faz a conta parecer robô.
- A nutricionista mostrou como ela escreve (uma mensagem dela, um "eu falo assim")? Siga o jeito dela no lugar do registro padrão, mantendo os 4 elementos e a régua.

## Três exemplos (terça, 14h, nutri esportiva Ana)

Carol comentou "amei essa receita!" no post de panqueca proteica da Ana. Bio: "Mãe do Theo | Corredora amadora | Floripa".

```json
"carol.runs": {"partes": [
  "Oi, Carol, boa tarde!",
  "Vi que vc comentou na minha receita de panqueca proteica",
  "Vi tb que vc corre, tá treinando pra alguma prova?",
  "Se precisar de algo, conta comigo. Uma boa terça pra vc 😊"],
 "porque": "comentou num post seu; corredora, público de nutri esportiva"}
```

Rafael curtiu um post de concorrente. Bio: "Engenheiro | CrossFit 5x/semana | Curitiba".

```json
"rafa_crossfit": {"partes": [
  "Oi, Rafael, boa tarde!",
  "Sou a Ana, nutri aqui do Insta, e vi que vc faz CrossFit 5x na semana",
  "Já compete ou treina mais por saúde?",
  "Se precisar de algo, conta comigo. Bom treino e uma boa terça!"],
 "porque": "curtiu post de concorrente; treina 5x por semana"}
```

Juliana comentou "preciso muito disso" num post de concorrente sobre compulsão à noite. Bio: "Advogada | 40+ | buscando equilíbrio". A dor fica de fora da mensagem.

```json
"ju.lima": {"partes": [
  "Oi, Juliana, boa tarde!",
  "Sou a Ana, nutri aqui do Insta, e vi no seu perfil que vc é advogada",
  "Atua em qual área?",
  "Se precisar de algo, conta comigo. Uma boa terça pra vc!"],
 "porque": "comentou em post de concorrente sobre fome à noite; 40+"}
```

## Depois que ela responde

- Respondeu com texto: avance. Responda do tamanho que ela respondeu, só um pouco mais.
- Faça uma pergunta fácil, que nasce do que ela disse, sobre a rotina dela. Evite pergunta ampla e íntima ("qual sua maior dificuldade?"): parece formulário.
- Uma pergunta por vez. Em 4 ou 5 perguntas já dá para saber se faz sentido oferecer.
- Ela contou uma dificuldade ou um desejo: acolha e ofereça ajuda dizendo o que ela ganha, com o nome dela. Não prometa resultado.
- A conversa rende há dias sem dor aparecendo: pergunte direto qual é a expectativa dela. Sim ou não liberam o seu tempo; o "talvez" eterno toma o tempo de quem compraria.
- Pediu para não ser contatada: `marcar @perfil --status descartado --obs "pediu para parar"`, na hora.

## Sem resposta

- É o normal: a maioria não responde.
- Depois de 3 dias, não mande outra mensagem. Interaja no conteúdo dela: responda um story ou comente um post com algo específico do que ela publicou. Marque `segundo-toque`. Perfil fechado: pule o toque e marque `segundo-toque` com `--obs "fechado, sem toque"`.
- Mais 7 dias sem resposta: `encerrado`. Não insista uma terceira vez.
