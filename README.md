# cass-vendas

Plugin com skills de vendas para nutricionistas. Funciona no Claude Code e no Codex.

## O que vem dentro

**`prospectar-pacientes`**: acha pacientes em potencial no Instagram entre quem curtiu e comentou nos posts recentes do seu perfil e de perfis concorrentes.

- Pergunta o seu @ e os concorrentes no começo de cada rodada.
- Lê o seu perfil e confirma com você quem é o seu paciente.
- Coleta as curtidas e os comentários pelo Apify, com a **sua** chave.
- Tira quem tem 2.000 seguidores ou menos, quem vende na mesma área, marcas e lojas.
- Escreve a primeira mensagem de cada pessoa em 4 partes, sem oferta.
- Entrega uma planilha Excel e um painel HTML com botão de copiar.
- Guarda um registro no seu computador para não sugerir a mesma pessoa duas vezes e lembra quem retomar.

A skill **não envia mensagem**: você copia, cola e envia. Ela não entra no Instagram com a sua conta.

## O que você precisa

- Python 3.9 ou mais novo.
- Uma conta no [Apify](https://apify.com) e a sua chave (Settings > API & Integrations > Personal API tokens). O plano grátis dá US$ 5 por mês; uma rodada pequena gasta perto de US$ 0,50. A skill mostra o custo e pede o seu sim antes de coletar.

Na primeira rodada a skill abre um arquivo de texto para você colar a chave. A chave fica só no seu computador, em `~/.config/prospectar-pacientes/apify.txt`. Não cole a chave no chat.

## Instalar

**Claude Code**

```
/plugin marketplace add cassianodiniz/cass-vendas
/plugin install cass-vendas@cass-vendas
```

**Codex**

```bash
codex plugin marketplace add https://github.com/cassianodiniz/cass-vendas.git
codex plugin add cass-vendas
```

No Codex, a coleta precisa de acesso à internet (api.apify.com) e de gravar em `~/prospectar-pacientes` e `~/.config/prospectar-pacientes`. O modo padrão do Codex bloqueia isso: autorize quando ele pedir, ou abra o Codex com acesso à rede.

## Usar

Peça em linguagem normal: "prospecta pacientes pra mim", "quais pacientes eu abordo hoje", "enviei a 1, 3 e 5", "quem falta retomar", "como foi a prospecção da semana".

## Dados e limites

- Só dados públicos, lidos pelo Apify. A coleta automática vai contra os termos de uso da Meta; use por sua conta e risco.
- O registro das pessoas fica só no seu computador, em `~/prospectar-pacientes/`. Não copie para nuvem nem compartilhe.
- Nenhuma mensagem promete resultado ou comenta corpo e peso.
