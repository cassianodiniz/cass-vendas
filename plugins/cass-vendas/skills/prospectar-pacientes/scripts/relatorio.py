"""Planilha Excel e painel HTML da prospecção de pacientes. Só biblioteca padrão do Python."""
from __future__ import annotations

import json
import re
import zipfile
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape
try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # Windows sem o pacote tzdata
    from datetime import timedelta, timezone
    FUSO = timezone(timedelta(hours=-3), "BRT")
ASSETS = Path(__file__).resolve().parent.parent / "assets"

# ---------------------------------------------------------------- conferência mecânica da mensagem

EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿\U0001F000-\U0001F2FF]")
REGRAS = [
    ("sem travessão", re.compile(r"[—–]")),
    ("sem negrito", re.compile(r"\*\*|__")),
    ("sem oferta, link ou serviço na primeira mensagem",
     re.compile(r"consulta|atendo\b|atendimento|agend|acompanhamento|plano alimentar|desconto|promo|https?://|www\.|\blink\b", re.I)),
    ("palavra fora da régua", re.compile(r"\b(adorei|gostei demais|gostei muito|top demais|lindo demais|rolar|rola|rolou|"
                                          r"pegada|de verdade|de fato|realmente|game changer|vale ouro|constância|consistência)\b", re.I)),
    ("sem dizer o que a pessoa sente", re.compile(r"\b(imagino que|sei como|deve ser difícil|você deve|vc deve)\b", re.I)),
    ("sem pedir desculpa pelo contato", re.compile(r"desculp|não quero (te )?incomodar|sem compromisso", re.I)),
    ("sem 'não é X, é Y'", re.compile(r"\bnão é\b[^.?!\n]{1,60},\s*é\b", re.I)),
]


def conferir_mensagem(texto: str) -> list[tuple[str, str]]:
    achados = []
    for nome, padrao in REGRAS:
        m = padrao.search(texto)
        if m:
            achados.append((nome, m.group(0)))
    if len(EMOJI.findall(texto)) > 1:
        achados.append(("no máximo 1 emoji", "".join(EMOJI.findall(texto))))
    if texto.count("?") > 1:
        achados.append(("uma pergunta só", f"{texto.count('?')} perguntas"))
    palavras = len(texto.split())
    if palavras > 55:
        achados.append(("curta: até umas 45 palavras", f"{palavras} palavras"))
    return achados


SAUDACAO = re.compile(r"\bbo[am] (dia|tarde|noite)\b", re.I)
DIA = re.compile(r"segunda|ter[çc]a|quarta|quinta|sexta|s[áa]bado|domingo|fim de semana|\bfds\b|semana|feriado", re.I)


def conferir_partes(partes: list[str]) -> list[tuple[str, str]]:
    """Conferência mecânica mínima das partes 1 e 4. O conteúdo das partes 2 e 3 é conferido por quem escreve."""
    achados = []
    if not SAUDACAO.search(partes[0]):
        achados.append(("parte 1 precisa do nome e da saudação do horário (bom dia, boa tarde, boa noite)", partes[0]))
    if len(SAUDACAO.sub("", re.sub(r"\b(oi|ol[áa]|e a[íi])\b", "", partes[0], flags=re.I)).strip(" ,!.")) < 2:
        achados.append(("parte 1 precisa do primeiro nome da pessoa", partes[0]))
    if not DIA.search(partes[3]):
        achados.append(("parte 4 precisa do dia da semana no tchau (ex.: uma boa terça)", partes[3]))
    return achados


# ---------------------------------------------------------------- planilha (xlsx escrito à mão)

def _col(n: int) -> str:
    s = ""
    while n:
        n, r = divmod(n - 1, 26)
        s = chr(65 + r) + s
    return s


INVALIDO_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")


def _cel(ref: str, valor, estilo: int = 0) -> str:
    if valor is None or valor == "":
        return f'<c r="{ref}" s="{estilo}"/>'
    if isinstance(valor, (int, float)) and not isinstance(valor, bool):
        return f'<c r="{ref}" s="{estilo}"><v>{valor}</v></c>'
    if isinstance(valor, tuple) and valor[0] == "link":
        _, url, rotulo = valor
        rotulo = INVALIDO_XML.sub("", rotulo)
        f = escape(f'HYPERLINK("{url}","{rotulo}")')
        return f'<c r="{ref}" s="3" t="str"><f>{f}</f><v>{escape(rotulo)}</v></c>'
    texto = escape(INVALIDO_XML.sub("", str(valor))).replace("\n", "&#10;")
    return f'<c r="{ref}" s="{estilo}" t="inlineStr"><is><t xml:space="preserve">{texto}</t></is></c>'


def _aba(linhas: list[list], larguras: list[int], cabecalho_na_linha: int | None = 1, filtro: bool = True,
         estilos_por_linha: dict[int, int] | None = None, alturas: dict[int, float] | None = None) -> str:
    estilos_por_linha = estilos_por_linha or {}
    alturas = alturas or {}
    cols = "".join(f'<col min="{i}" max="{i}" width="{w}" customWidth="1"/>' for i, w in enumerate(larguras, 1))
    corpo = []
    for r, linha in enumerate(linhas, 1):
        est = 1 if r == cabecalho_na_linha else estilos_por_linha.get(r, 2)
        ht = f' ht="{alturas[r]}" customHeight="1"' if r in alturas else ""
        cels = "".join(_cel(f"{_col(c)}{r}", v, est) for c, v in enumerate(linha, 1))
        corpo.append(f'<row r="{r}"{ht}>{cels}</row>')
    painel = ""
    if cabecalho_na_linha:
        painel = (f'<sheetViews><sheetView workbookViewId="0"><pane ySplit="{cabecalho_na_linha}" '
                  f'topLeftCell="A{cabecalho_na_linha + 1}" activePane="bottomLeft" state="frozen"/></sheetView></sheetViews>')
    auto = ""
    if filtro and cabecalho_na_linha and len(linhas) > cabecalho_na_linha:
        auto = f'<autoFilter ref="A{cabecalho_na_linha}:{_col(len(larguras))}{len(linhas)}"/>'
    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'{painel}<cols>{cols}</cols><sheetData>{"".join(corpo)}</sheetData>{auto}</worksheet>')


ESTILOS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<fonts count="5">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFFFFFFF"/><name val="Calibri"/></font>
<font><u/><sz val="11"/><color rgb="FF1155CC"/><name val="Calibri"/></font>
<font><b/><sz val="16"/><name val="Calibri"/></font>
<font><b/><sz val="12"/><name val="Calibri"/></font>
</fonts>
<fills count="3"><fill><patternFill patternType="none"/></fill><fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF14532D"/><bgColor indexed="64"/></patternFill></fill></fills>
<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="6">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="0" xfId="0" applyFont="1" applyFill="1" applyAlignment="1"><alignment vertical="center" wrapText="1"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
<xf numFmtId="0" fontId="2" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top"/></xf>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="4" fillId="0" borderId="0" xfId="0" applyFont="1" applyAlignment="1"><alignment vertical="top" wrapText="1"/></xf>
</cellXfs>
</styleSheet>"""


def _xlsx(caminho: Path, abas: list[tuple[str, str]]) -> None:
    tipos = "".join(f'<Override PartName="/xl/worksheets/sheet{i}.xml" '
                    'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
                    for i in range(1, len(abas) + 1))
    with zipfile.ZipFile(caminho, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                   '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                   '<Default Extension="xml" ContentType="application/xml"/>'
                   '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
                   '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
                   f'{tipos}</Types>')
        z.writestr("_rels/.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
                   '</Relationships>')
        folhas = "".join(f'<sheet name="{escape(n)}" sheetId="{i}" r:id="rId{i}"/>' for i, (n, _) in enumerate(abas, 1))
        z.writestr("xl/workbook.xml",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
                   'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   f'<sheets>{folhas}</sheets><calcPr calcId="0" fullCalcOnLoad="1"/></workbook>')
        rels = "".join(f'<Relationship Id="rId{i}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
                       f'Target="worksheets/sheet{i}.xml"/>' for i in range(1, len(abas) + 1))
        rels += (f'<Relationship Id="rId{len(abas) + 1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" '
                 'Target="styles.xml"/>')
        z.writestr("xl/_rels/workbook.xml.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{rels}</Relationships>')
        z.writestr("xl/styles.xml", ESTILOS)
        for i, (_, xml) in enumerate(abas, 1):
            z.writestr(f"xl/worksheets/sheet{i}.xml", xml)


def _o_que_fez(lead: dict) -> str:
    partes = []
    for i in lead["interacoes"]:
        t = f"{i['tipo']} em @{i['conta']}"
        if i.get("comentario"):
            t += f': "{i["comentario"]}"'
        partes.append(t)
    return "\n".join(partes)


def _altura(*pares: tuple[str, int]) -> float:
    """Altura da linha pelo texto mais alto; cada par é (texto, caracteres que cabem por linha)."""
    linhas = max(sum(max(1, -(-len(l) // largura)) for l in (t or "").split("\n")) for t, largura in pares)
    return min(409, 15 * max(1, linhas) + 4)


def planilha(caminho: Path, dados: dict, escolhidos: list[dict], reg: dict, cfg: dict) -> None:
    # Aba 1: lista do dia, na ordem de envio.
    linhas = [["#", "Nota", "Nome", "Instagram", "Seguidores", "De onde veio", "O que a pessoa fez", "Bio",
               "Mensagem pronta (copie e cole no Direct)", "Status (escreva: enviei, respondeu, não quer)"]]
    alturas = {}
    for n, l in enumerate(escolhidos, 1):
        linhas.append([n, l["nota"], l["nome"], ("link", l["link"], "@" + l["perfil"]), l["seguidores"],
                       "Seu perfil" if l["origem"] == "seu perfil" else "Concorrente",
                       _o_que_fez(l), l["bio"], l["mensagem"], ""])
        alturas[n + 1] = _altura((l["mensagem"], 58), (l["bio"], 44), (_o_que_fez(l), 36))
    aba1 = _aba(linhas, [5, 6, 22, 22, 11, 13, 34, 40, 52, 22], alturas=alturas)

    # Aba 2: como usar.
    f = dados["funil"]
    como = [
        ["Como usar esta planilha"],
        [f"Prospecção de @{cfg['eu']} · rodada {dados['rodada'].replace('_', ' ')} (horário de Brasília)"],
        [""],
        ["O que foi feito"],
        [f"1. Li os {dados['posts_lidos']} posts mais recentes do seu perfil e dos concorrentes: "
         + ", ".join(dados["contas_lidas"]) + "."],
        [f"2. Juntei {f['interacoes_lidas']} curtidas e comentários, de {f['pessoas_unicas']} pessoas diferentes."],
        [f"3. Conferi {f['conferidas']} perfis e tirei quem tem {cfg.get('min_seguidores', 2000)} seguidores ou menos, "
         "quem vende na mesma área (nutrição, treino, estética, suplemento), marca ou loja."
         + (f" Somei {f.get('vistos_antes_sem_mensagem', 0) + f.get('vieram_da_fila_da_rodada_anterior', 0)} pessoas de rodadas anteriores que ainda não tinham mensagem."
            if f.get('vistos_antes_sem_mensagem', 0) + f.get('vieram_da_fila_da_rodada_anterior', 0) else "")],
        [f"4. Sobraram {f['passaram_no_filtro']} pessoas. As {len(escolhidos)} da aba \"Leads de hoje\" têm mensagem pronta."],
        [""],
        ["Como abordar (os 4 elementos da primeira mensagem)"],
        ["1. Nome + hora do dia: \"Oi, Carol, boa tarde!\""],
        ["2. O motivo: por que você está chamando. Se a pessoa interagiu no SEU perfil, diga o que ela fez. "
         "Se veio de concorrente, o motivo vem do perfil dela (nunca diga onde você a achou)."],
        ["3. O relacionamento: um fato do perfil dela e, se couber, uma pergunta leve sobre esse fato."],
        ["4. O dia + o tchau: \"Se precisar de algo, conta comigo. Uma boa terça pra vc!\""],
        ["Sem oferta, sem link e sem falar de consulta na primeira mensagem. O objetivo é só ela responder."],
        [""],
        ["Ordem de envio"],
        ["Comece pelo topo: quem comentou no seu perfil, depois quem curtiu, depois quem veio dos concorrentes."],
        ["Mande de 8 a 10 por dia, num horário fixo, com as notificações desligadas."],
        [""],
        ["Depois de enviar"],
        ["Escreva \"enviei\" na coluna Status e avise no chat quais você mandou (ex.: 1, 3, 5), para o registro não sugerir de novo."],
        ["Não respondeu em 3 dias: não mande outra mensagem. Responda um story ou comente um post dela."],
        ["Mais 7 dias sem resposta: encerre e siga para a próxima pessoa."],
        ["Respondeu: responda do tamanho que ela respondeu e faça uma pergunta fácil sobre a rotina dela. "
         "Quando ela contar uma dificuldade, acolha e ofereça ajuda dizendo o que ela ganha."],
    ]
    titulos = {1: 4, 4: 5, 10: 5, 17: 5, 21: 5}
    aba2 = _aba(como, [120], cabecalho_na_linha=None, filtro=False, estilos_por_linha=titulos)

    # Aba 3: todos os encontrados nesta rodada.
    todos = [["Instagram", "Nome", "Seguidores", "De onde veio", "O que a pessoa fez", "Nota", "Resultado do filtro"]]
    for l in dados["leads"] + dados["descartados"]:
        todos.append([("link", l["link"], "@" + l["perfil"]), l["nome"], l["seguidores"],
                      "Seu perfil" if l["origem"] == "seu perfil" else "Concorrente", _o_que_fez(l), l["nota"],
                      "passou" if l["etapa"] != "descartado" else "fora: " + l["obs"]])
    aba3 = _aba(todos, [24, 24, 11, 13, 50, 6, 50])

    # Aba 4: histórico de todas as rodadas.
    hist = [["Instagram", "Nome", "Etapa", "De onde veio", "Visto em", "Sugerido em", "Abordado em", "Observação"]]
    ordem = {"respondeu": 0, "virou-paciente": 0, "abordado": 1, "segundo-toque": 1, "sugerido": 2, "visto": 3, "encerrado": 4, "descartado": 5}
    for l in sorted(reg.values(), key=lambda x: (ordem.get(x["etapa"], 9), x["perfil"])):
        hist.append([("link", l["link"], "@" + l["perfil"]), l.get("nome"), l["etapa"], l.get("origem"),
                     l.get("visto_em"), l.get("sugerido_em"), l.get("abordado_em"), l.get("obs")])
    aba4 = _aba(hist, [24, 24, 14, 13, 12, 12, 12, 50])

    _xlsx(caminho, [("Leads de hoje", aba1), ("Como usar", aba2), ("Todos desta rodada", aba3), ("Histórico", aba4)])


# ---------------------------------------------------------------- painel HTML

def painel(caminho: Path, dados: dict, escolhidos: list[dict], cfg: dict) -> None:
    modelo = (ASSETS / "painel.html").read_text(encoding="utf-8")
    por_origem = {"Comentou no seu": 0, "Curtiu no seu": 0, "Comentou em concorrente": 0, "Curtiu em concorrente": 0}
    for l in dados["leads"]:
        lados = {(i["lado"], i["tipo"]) for i in l["interacoes"]}
        if ("eu", "comentou") in lados:
            por_origem["Comentou no seu"] += 1
        elif ("eu", "curtiu") in lados:
            por_origem["Curtiu no seu"] += 1
        elif ("concorrente", "comentou") in lados:
            por_origem["Comentou em concorrente"] += 1
        else:
            por_origem["Curtiu em concorrente"] += 1
    payload = {
        "perfil": cfg["eu"], "publico": cfg.get("publico") or "", "minimo": cfg.get("min_seguidores", 2000),
        "rodada": dados["rodada"], "gerado": datetime.now(FUSO).strftime("%d/%m/%Y às %Hh%M"),
        "contas": dados["contas_lidas"], "posts": dados["posts_lidos"], "funil": dados["funil"],
        "descartes": dados.get("descartes_por_motivo", {}), "por_origem": por_origem,
        "leads": [{"n": n, "perfil": l["perfil"], "link": l["link"], "nome": l["nome"], "seguidores": l["seguidores"],
                   "origem": l["origem"], "nota": l["nota"], "porque": l["porque"], "fez": _o_que_fez(l),
                   "partes": l["partes"]} for n, l in enumerate(escolhidos, 1)],
    }
    js = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    caminho.write_text(modelo.replace("/*DADOS*/null", js), encoding="utf-8")
