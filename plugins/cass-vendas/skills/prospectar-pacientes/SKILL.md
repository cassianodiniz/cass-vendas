---
name: prospectar-pacientes
description: Use quando uma nutricionista quer achar pacientes novos no Instagram entre quem curtiu ou comentou nos posts dela ou de perfis concorrentes, ou tocar essa rotina de prospecção de pacientes — "prospectar pacientes", "achar pacientes no Instagram", "quais pacientes eu abordo hoje", "monta minha lista de pacientes", "mandei pras pacientes 1, 3 e 5", "a paciente respondeu", "quais pacientes falta retomar", "como foi a prospecção de pacientes". Não use para achar nutricionistas para vender mentoria, para achar negócio local com site fraco, nem para responder uma conversa de venda que já está em andamento.
---

# Prospectar pacientes

Acha pacientes em potencial entre quem curtiu e comentou nos posts recentes da nutricionista e dos concorrentes, filtra quem vale a abordagem, escreve a primeira mensagem com os 4 elementos e entrega uma planilha Excel e um painel HTML. Guarda um registro para nunca sugerir a mesma pessoa duas vezes (quem foi conferido e ainda não recebeu mensagem continua disponível nas próximas rodadas).

Quem usa é a nutricionista (pode ser qualquer aluna, em qualquer computador). Fale com ela pelo nome dela, nunca presuma quem é.

Todos os comandos são de `scripts/prospectar.py` (rode com `python3` a partir da pasta desta skill; `--help` mostra as opções). Os arquivos ficam em `~/prospectar-pacientes/<perfil>/`, separados por @: cada aluna tem os seus concorrentes, público e registro. Datas e horas sempre no horário de Brasília.

## Rotinas

| Ela diz | Faça |
|---|---|
| "prospecta pacientes", "quais pacientes eu abordo hoje" | Rodada (passos 1 a 6) |
| "enviei a 1, 3 e 5", "a fulana respondeu", "essa pediu pra parar" | Registrar |
| "quem falta retomar" | Pendentes |
| "como foi a semana" | Resumo |

## Rodada

### 1. Perfil e concorrentes (a primeira mensagem de toda rodada)

Antes de qualquer outra coisa, rode `perfil` (sem opções: só mostra, não grava nada) e pergunte numa mensagem só:

1. Sem perfil salvo: "Qual é o seu @ no Instagram?" Com perfil salvo: "Sigo com o @fulana?"
2. "Eu leio quem curtiu e comentou nos perfis @a, @b e @c. Quer adicionar algum concorrente ou trocar algum desses?" Liste os concorrentes salvos desse @; sem nada salvo, os três padrão: @nutrilucasstein, @dralainemoser e @nutrijoaomuzzy.

Grave a resposta: `perfil --eu @dela --concorrentes @novo1 @novo2` (soma à lista atual ou aos três padrão), `--tirar @x` para remover um, `--sem-padrao --concorrentes @a @b` para trocar todos. Trocar de @ carrega as preferências daquele @, nunca as de outra pessoa.

### 2. Chave do Apify

Rode `status`.

- `"chave": "ausente"`: rode `configurar`. Ele cria o arquivo da chave e abre no editor de texto. Diga a ela: "Abri um arquivo de texto. Cole nele a sua chave do Apify (apify.com > Settings > API & Integrations > Personal API tokens), salve e me avise." Não peça a chave no chat. Se ela colar a chave no chat mesmo assim, grave no arquivo que o `configurar` mostrou e não repita a chave em nenhuma resposta.
- Chave recusada ou sem conexão: mostre o erro real do `status` e pare.
- Funcionou: guarde `sobra_usd` da primeira chave que funcionou para o passo 4.

### 3. Público-alvo

Primeira rodada desse perfil (o `perfil` mostra `"falta": ["publico"]`):

1. Rode `ler-perfil` (custa centavos: teto de US$ 0,05). Leia a bio e as legendas dos posts recentes.
2. Proponha em uma linha quem é o paciente dela e as palavras que esse paciente põe na bio. Exemplo: "Pelo seu perfil, o seu paciente é quem treina e quer ganhar massa ou melhorar o desempenho, em Porto Alegre ou online. Vou priorizar quem tem na bio: treino, crossfit, corrida, academia, atleta. Está certo?"
3. Com o sim (ou a correção dela): `perfil --publico "..." --palavras treino,crossfit,corrida --cidade "Porto Alegre"`. Cidade só se ela atende presencial.

Rodadas seguintes: mostre o público salvo e pergunte se continua o mesmo.

O lead precisa ter mais de 2.000 seguidores (2.000 exatos fica fora). Só mude com `--min-seguidores` se ela pedir.

### 4. Custo e coleta

1. Rode `estimar` e diga a ela: "Esta rodada deve custar uns US$ X no Apify (`custo_provavel_usd`), e eu travo o gasto em no máximo US$ T (`teto_usd`). Você tem US$ Y este mês. Posso rodar?"
2. Teto maior que a sobra: rode de novo com `--posts 1 --curtidas 30 --max-perfis 60` e mostre o novo teto. Ainda não cabe: pare e diga que o saldo do mês não cobre esta rodada.
3. Com o sim: rode `coletar` com as mesmas opções. Leva de 2 a 10 minutos; avise que está coletando.

### 5. Escolher e escrever

Abra `references/abordagem.md` e siga. Depois:

1. Leia os `leads` que o `coletar` devolveu. Eles já vêm na ordem de envio (grupo de origem primeiro, nota depois). Pegue os primeiros, até 10 (ou o número que ela pediu). Leia a bio de cada um:
   - motivo com `CONFIRA`: decida pela bio se é pessoa (fica) ou negócio (sai);
   - quem a referência manda tirar: `marcar @perfil --status descartado --obs "motivo"`;
   - sem fato para o relacionamento nesta rodada: deixe de fora sem marcar nada (continua disponível).
2. Escreva a mensagem de cada um com as 4 partes. Grave tudo em `mensagens.json`, na pasta da rodada (`pasta` no resultado do `coletar`), neste formato:

   ```json
   {"perfil1": {"partes": ["Nome + hora", "Motivo", "Relacionamento", "Dia + tchau"], "porque": "uma frase"}}
   ```

3. Antes de rodar o relatório, confira cada mensagem você mesmo, parte por parte:
   - parte 1 tem o primeiro nome e a saudação do horário de agora;
   - parte 2: veio do seu perfil, diz o que a pessoa fez e em qual post; veio de concorrente, diz quem você é e um fato do perfil dela, sem citar concorrente nem comentário;
   - parte 3 tem um fato do perfil e no máximo uma pergunta sobre esse fato;
   - parte 4 tem o dia da semana de hoje e o tchau.
4. Rode `relatorio --mensagens <pasta da rodada>/mensagens.json`. Ele faz a conferência mecânica (palavras, oferta, emoji, tamanho, saudação, dia, @ de concorrente, etapa no registro) e só gera os arquivos se todas passarem. Recusou: corrija as mensagens apontadas e rode de novo. Recusou duas vezes a mesma pessoa: tire-a da lista desta rodada sem marcar nada.

### 6. Entregar

1. Abra o painel no navegador (`open` no Mac, `start` no Windows) e diga onde estão a planilha e o painel (caminho completo).
2. No chat, uma linha por pessoa, numerada, na ordem de envio: nome, link do perfil, de onde veio e, em uma frase, por que ela. Logo abaixo, a mensagem num bloco só dela, pronta para copiar.
3. Feche com: "Me diz quais você enviou (ex.: 1, 3, 5) que eu registro."

Se a coleta devolveu poucos leads, diga por quê com os números do `funil` e de `descartes_por_motivo`, e sugira ler mais posts ou outro concorrente. Não baixe o mínimo de seguidores por conta própria.

Ela pede para ver a lista de novo: abra o painel da rodada (está na pasta). Rodar o `relatorio` de novo com as mesmas pessoas só funciona na mesma rodada; numa rodada nova, quem já foi sugerido não volta.

## Registrar

Ela fala em números ("enviei a 1, 3 e 5"): os números são os da última lista que você entregou (a do painel e da planilha). Troque cada número pelo @ antes de marcar. Sem a lista na conversa, abra o painel da última rodada e confirme os @ com ela.

- Enviou: `marcar @a @b --status abordado`.
- Respondeu: `marcar @a --status respondeu`. Ajude na conversa com a seção "Depois que ela responde" de `references/abordagem.md`.
- Fechou consulta: `marcar @a --status virou-paciente`.
- Não quer, pediu para parar, não era o público: `marcar @a --status descartado --obs "motivo"`. Nunca volta para a lista.

## Pendentes

Rode `pendentes`.

- `interagir_no_conteudo_hoje`: abordadas há 3 dias ou mais, sem resposta. Não é outra mensagem no Direct. Entregue o link do perfil e uma sugestão de resposta a um story ou comentário num post recente dela. Ela faz e você marca `marcar @a --status segundo-toque`. Perfil fechado, sem conteúdo visível: não há toque possível; marque `marcar @a --status segundo-toque --obs "fechado, sem toque"` para contar os 7 dias.
- `encerrar`: segundo toque há 7 dias sem resposta. Marque `marcar @a --status encerrado`.
- `sugeridos_sem_retorno`: pergunte se ela enviou alguma dessas.

## Resumo

Rode `resumo --dias 7` (ou o período que ela pedir). Mostre abordagens, respostas e pacientes por origem (seu perfil ou concorrente) e diga em uma frase onde vale pôr o esforço. Com menos de 30 abordagens numa origem, diga que ainda é cedo para comparar.

## Quando algo falha

| Falha | Faça |
|---|---|
| `coletar` diz "nenhum post com interação" | Nenhuma conta lida teve post recente, fora os fixados, com curtida ou comentário visível (conta fechada, sem posts ou sem interação). Diga quais (`contas_sem_posts`) e peça outro concorrente. |
| Uma conta em `contas_sem_posts`, as outras ok | Siga com as outras e avise qual ficou de fora. |
| Erro do Apify no meio da coleta | Mostre o erro real. Saldo não cobre: diga e pare. Outro erro: rode `coletar` mais uma vez (avise que pode gastar de novo até o teto); falhou de novo, pare e mostre o erro. |
| `python3` não existe | Diga que a skill precisa do Python 3.9 ou mais novo instalado e pare. |
| Erro "sem acesso à internet neste ambiente" ou "não consegui gravar" (sandbox do Codex) | O script precisa de rede (api.apify.com) e de gravar em `~/prospectar-pacientes` e `~/.config/prospectar-pacientes`. Se o ambiente oferece pedir permissão para sair do sandbox, rode o mesmo comando de novo pedindo. Não oferece, ou ela negou: explique que a coleta não roda neste modo e que ela precisa abrir o Codex com acesso à rede e a essas pastas; pare. |
| `relatorio` diz que a rodada é de outro @ | Confirme com ela qual @ usar e rode `perfil --eu @certo` antes. |

## Limites

- Só dados públicos, lidos pelo Apify. Não entre no Instagram com a conta dela e não use extensão logada para coletar: a Meta proíbe coleta automática e a restrição cairia na conta dela. A coleta pelo Apify também vai contra os termos da Meta. Diga isso na primeira rodada, sem prometer que não há risco.
- Nunca envie mensagem por ela. Ela copia, cola e envia.
- O registro fica só no computador dela (`~/prospectar-pacientes/`). Não copie para repositório, nuvem ou grupo. O registro guarda perfil, nome, bio, seguidores, origem, posts em que a pessoa interagiu, nota, etapa e datas. O comentário que a pessoa escreveu fica só no arquivo da rodada.
- Sem promessa de resultado e sem comentário sobre corpo ou peso, em nenhuma mensagem (regra do Conselho de Nutricionistas e respeito básico).
