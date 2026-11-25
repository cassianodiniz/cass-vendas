#!/usr/bin/env python3
"""Prospecção de pacientes no Instagram para nutricionistas.

Acha quem curtiu e comentou nos posts recentes do seu perfil e dos perfis
concorrentes, confere cada pessoa (seguidores, bio, perfil aberto) e guarda um
registro para nunca sugerir a mesma pessoa duas vezes. Usa a chave do Apify da
própria nutricionista. Não entra no Instagram e não usa a conta de ninguém.

    python3 prospectar.py configurar                 # cria o arquivo da chave do Apify e abre para colar
    python3 prospectar.py status                     # confere a chave e o crédito do mês
    python3 prospectar.py perfil --eu @seuperfil [--concorrentes @a @b] [--publico "..."] [--palavras a,b] [--cidade X]
    python3 prospectar.py perfil                     # mostra a configuração atual
    python3 prospectar.py ler-perfil [@perfil]       # bio e posts recentes, para entender o público-alvo
    python3 prospectar.py estimar [opções do coletar]
    python3 prospectar.py coletar [--posts 2] [--curtidas 60] [--comentarios 40] [--max-perfis 120]
    python3 prospectar.py relatorio --mensagens mensagens.json [--rodada ultima]
    python3 prospectar.py marcar --status abordado @a @b [--obs "..."]
    python3 prospectar.py pendentes
    python3 prospectar.py resumo [--dias 30]

Os arquivos ficam em ~/prospectar-pacientes/<seu perfil>/ (mude com a
variável PROSPECTAR_PACIENTES_DIR). Datas no horário de Brasília.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
try:
    from zoneinfo import ZoneInfo
    FUSO = ZoneInfo("America/Sao_Paulo")
except Exception:  # Windows sem o pacote tzdata. O Brasil não tem horário de verão.
    from datetime import timezone
    FUSO = timezone(timedelta(hours=-3), "BRT")

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))

BASE = Path(os.environ.get("PROSPECTAR_PACIENTES_DIR", Path.home() / "prospectar-pacientes"))
ARQ_CHAVE = Path.home() / ".config" / "prospectar-pacientes" / "apify.txt"
CHAVES_EXTRAS: list[Path] = []

CONCORRENTES_PADRAO = ["nutrilucasstein", "dralainemoser", "nutrijoaomuzzy"]
MIN_SEGUIDORES = 2000
MAX_SEGUIDORES = 100_000

ETAPAS = ["visto", "sugerido", "abordado", "segundo-toque", "respondeu", "virou-paciente", "encerrado", "descartado"]

# Coletores do Apify. Os preços (US$ por item, plano grátis) foram lidos na loja do Apify em 25/11/2026.
POSTS = "apify~instagram-post-scraper"
ENGAJAMENTO = "scraping_solutions~instagram-engagers-likes-and-comments-no-cookies"
PERFIS = "apify~instagram-profile-scraper"
PRECO = {POSTS: 0.0017, ENGAJAMENTO: 0.00065, PERFIS: 0.0026}

# Quem não é paciente: quem vende na mesma área (nutrição, treino, suplemento, comida, estética) e marcas.
# Profissional de outra área (dentista, médica, advogada) é paciente em potencial e fica.
NAO_PACIENTE = [
    r"nutri", r"\bcrn\b", r"crn[\s\-/.:]*\d", r"personal\s*trainer", r"\bpersonal\b", r"treinador", r"\bcoach\b", r"\bcref\b",
    r"\bloja\b", r"\bstore\b", r"\bshop\b", r"suplement", r"\boficial\b", r"est[eé]tica", r"esteta",
    r"distribuidora", r"atacado", r"delivery", r"marmita", r"restaurante", r"farm[aá]cia",
]

# Termos que tanto podem ser negócio quanto profissional de outra área ("dentista | consultório próprio").
# Não descartam: baixam 1 ponto e pedem para conferir a bio antes de escrever.
REVISAR = [r"cl[ií]nica", r"consult[oó]rio"]

# Calor de cada origem (comentário antes de curtida, seu perfil antes do concorrente).
CALOR = {("eu", "comentou"): 6, ("eu", "curtiu"): 5, ("concorrente", "comentou"): 4, ("concorrente", "curtiu"): 3}


# ---------------------------------------------------------------- utilidades

def agora() -> datetime:
    return datetime.now(FUSO)


def hoje() -> str:
    return agora().strftime("%Y-%m-%d")


def limpa(perfil: str) -> str:
    perfil = perfil.strip().lower()
    m = re.search(r"instagram\.com/([a-z0-9._]+)", perfil)
    return (m.group(1) if m else perfil.lstrip("@")).strip("/")


def sair(msg: str) -> None:
    print("ERRO: " + msg, file=sys.stderr)
    sys.exit(1)


def mostrar(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=1))


def ler_json(caminho: Path, padrao):
    if caminho.is_file():
        return json.loads(caminho.read_text(encoding="utf-8"))
    return padrao


def gravar_json(caminho: Path, dados) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    tmp = caminho.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(caminho)


def cfg_do_perfil(eu: str) -> dict:
    """Preferências de um @ (concorrentes, público, palavras, cidade). Cada aluna tem as suas."""
    geral = ler_json(BASE / "config.json", {})
    cfg = ler_json(BASE / eu / "config.json", None)
    if cfg is None:  # versão antiga guardava tudo no arquivo geral; só vale para o mesmo @
        cfg = {k: v for k, v in geral.items() if k != "eu"} if geral.get("eu") == eu else {}
    cfg["eu"] = eu
    return cfg


def config() -> dict:
    eu = ler_json(BASE / "config.json", {}).get("eu")
    return cfg_do_perfil(eu) if eu else {}


def gravar_config(cfg: dict) -> None:
    gravar_json(BASE / "config.json", {"eu": cfg["eu"]})
    gravar_json(BASE / cfg["eu"] / "config.json", {k: v for k, v in cfg.items() if k != "eu"})


def pasta_do_perfil(cfg: dict | None = None) -> Path:
    cfg = cfg or config()
    if not cfg.get("eu"):
        sair("ainda não sei o seu perfil. Rode: perfil --eu @seuperfil")
    return BASE / cfg["eu"]


def registro_path() -> Path:
    return pasta_do_perfil() / "registro.json"


# ---------------------------------------------------------------- chave do Apify

def chaves() -> list[tuple[str, str]]:
    """Devolve (origem, chave). A chave nunca é impressa."""
    achadas = []
    if os.environ.get("APIFY_TOKEN"):
        achadas.append(("variável APIFY_TOKEN", os.environ["APIFY_TOKEN"].strip()))
    for arq in [ARQ_CHAVE, *CHAVES_EXTRAS]:
        if arq.is_file():
            for linha in arq.read_text(encoding="utf-8").splitlines():
                linha = linha.strip()
                if linha and not linha.startswith("#") and re.fullmatch(r"[A-Za-z0-9_\-]{20,}", linha):
                    achadas.append((str(arq), linha))
    vistas, unicas = set(), []
    for origem, chave in achadas:
        if chave not in vistas:
            vistas.add(chave)
            unicas.append((origem, chave))
    return unicas


def cmd_configurar(a) -> int:
    ARQ_CHAVE.parent.mkdir(parents=True, exist_ok=True)
    if not ARQ_CHAVE.is_file():
        ARQ_CHAVE.write_text(
            "# Cole aqui a sua chave do Apify (Personal API token), sozinha numa linha abaixo, e salve.\n"
            "# Onde achar: apify.com > Settings > API & Integrations > Personal API tokens.\n"
            "# Pode colar mais de uma chave, uma por linha: quando o crédito de uma acaba, uso a próxima.\n",
            encoding="utf-8")
    try:
        os.chmod(ARQ_CHAVE, 0o600)
    except OSError:
        pass
    if not a.nao_abrir:
        try:
            if sys.platform == "darwin":
                subprocess.run(["open", "-t", str(ARQ_CHAVE)], check=False)
            elif os.name == "nt":
                os.startfile(str(ARQ_CHAVE))  # type: ignore[attr-defined]
            else:
                subprocess.run(["xdg-open", str(ARQ_CHAVE)], check=False)
        except OSError:
            pass
    mostrar({"arquivo_da_chave": str(ARQ_CHAVE), "chaves_encontradas": len(chaves()),
             "proximo_passo": "colar a chave no arquivo aberto, salvar e rodar: status"})
    return 0


SANDBOX = ("sem acesso à internet neste ambiente. No Codex, o sandbox padrão bloqueia a rede: "
           "rode o comando de novo pedindo permissão para sair do sandbox.")


def sem_rede(e: Exception) -> bool:
    txt = str(e).lower()
    return "nodename" in txt or "name or service not known" in txt or "getaddrinfo" in txt or "temporary failure" in txt


def get_apify(caminho: str, chave: str) -> dict:
    req = urllib.request.Request("https://api.apify.com/v2" + caminho, headers={"Authorization": "Bearer " + chave})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode()).get("data", {})


def cmd_status(a) -> int:
    lista = chaves()
    if not lista:
        mostrar({"chave": "ausente", "arquivo_esperado": str(ARQ_CHAVE), "proximo_passo": "rodar: configurar"})
        return 1
    saida = []
    for i, (origem, chave) in enumerate(lista, 1):
        item = {"chave": f"nº {i}", "origem": origem}
        try:
            eu = get_apify("/users/me", chave)
            lim = get_apify("/users/me/limits", chave)
            usado = (lim.get("current") or {}).get("monthlyUsageUsd")
            teto = (lim.get("limits") or {}).get("maxMonthlyUsageUsd")
            item.update({"conta": eu.get("username"), "plano": (eu.get("plan") or {}).get("id"),
                         "gasto_no_mes_usd": round(usado or 0, 2), "limite_do_mes_usd": teto,
                         "sobra_usd": round((teto or 0) - (usado or 0), 2) if teto is not None else None})
        except urllib.error.HTTPError as e:
            item["erro"] = f"HTTP {e.code}: a chave foi recusada pelo Apify" if e.code in (401, 403) else f"HTTP {e.code}"
        except (urllib.error.URLError, TimeoutError) as e:
            item["erro"] = SANDBOX if sem_rede(e) else f"sem conexão com o Apify ({e})"
        saida.append(item)
    cfg = config()
    mostrar({"chaves": saida, "perfil_configurado": cfg.get("eu"), "pasta_dos_arquivos": str(BASE)})
    return 0 if any("erro" not in s for s in saida) else 1


def apify(coletor: str, entrada: dict, teto_usd: float) -> list[dict]:
    """Roda um coletor e espera o fim. Chave recusada ou sem crédito: tenta a próxima."""
    lista = chaves()
    if not lista:
        sair("nenhuma chave do Apify. Rode: configurar")
    ultimo = ""
    for i, (_, chave) in enumerate(lista, 1):
        cab = {"Authorization": "Bearer " + chave, "Content-Type": "application/json"}
        q = urllib.parse.urlencode({"waitForFinish": 60, "maxTotalChargeUsd": f"{max(teto_usd, TETO_MINIMO):.2f}"})
        try:
            req = urllib.request.Request(f"https://api.apify.com/v2/acts/{coletor}/runs?{q}",
                                         data=json.dumps(entrada).encode(), headers=cab, method="POST")
            with urllib.request.urlopen(req, timeout=90) as r:
                run = json.loads(r.read().decode())["data"]
            inicio = time.time()
            while run.get("status") in ("READY", "RUNNING"):
                if time.time() - inicio > 900:
                    sair(f"o coletor {coletor} passou de 15 minutos. Tente de novo com menos posts.")
                req = urllib.request.Request(f"https://api.apify.com/v2/actor-runs/{run['id']}?waitForFinish=60", headers=cab)
                with urllib.request.urlopen(req, timeout=90) as r:
                    run = json.loads(r.read().decode())["data"]
            if run.get("status") != "SUCCEEDED":
                ultimo = f"chave nº {i}: o coletor terminou como {run.get('status')} ({run.get('statusMessage') or ''})"
                if "credit" in (run.get("statusMessage") or "").lower() or "limit" in (run.get("statusMessage") or "").lower():
                    continue
                break
            req = urllib.request.Request(
                f"https://api.apify.com/v2/datasets/{run['defaultDatasetId']}/items?clean=true&format=json", headers=cab)
            with urllib.request.urlopen(req, timeout=120) as r:
                dados = json.loads(r.read().decode())
            return dados if isinstance(dados, list) else []
        except urllib.error.HTTPError as e:
            corpo = e.read().decode(errors="replace")[:300]
            ultimo = f"chave nº {i}: HTTP {e.code} {corpo}"
            if e.code in (401, 402, 403, 429):
                continue
            break
        except (urllib.error.URLError, TimeoutError) as e:
            ultimo = SANDBOX if sem_rede(e) else f"chave nº {i}: sem conexão ({e})"
            break
    sair("o Apify não entregou os dados. " + ultimo)
    return []


# ---------------------------------------------------------------- configuração do perfil

def cmd_perfil(a) -> int:
    muda = a.eu or a.sem_padrao or any(v is not None for v in (a.concorrentes, a.tirar, a.publico, a.palavras, a.cidade, a.min_seguidores))
    cfg = cfg_do_perfil(limpa(a.eu)) if a.eu else config()
    if not muda:  # só mostra
        mostrar({"configuracao": cfg or None, "falta": [k for k in ("eu", "publico") if not cfg.get(k)]})
        return 0
    if a.concorrentes is not None:
        base = [] if a.sem_padrao else list(CONCORRENTES_PADRAO)
        cfg["concorrentes"] = list(dict.fromkeys(base + [limpa(c) for c in a.concorrentes]))
    elif a.sem_padrao:
        cfg["concorrentes"] = []
    elif "concorrentes" not in cfg and cfg.get("eu"):
        cfg["concorrentes"] = list(CONCORRENTES_PADRAO)
    if a.tirar:
        cfg["concorrentes"] = [c for c in cfg.get("concorrentes", []) if c not in {limpa(t) for t in a.tirar}]
    if a.publico is not None:
        cfg["publico"] = a.publico
    if a.palavras is not None:
        cfg["palavras"] = [p.strip().lower() for p in a.palavras.split(",") if p.strip()]
    if a.cidade is not None:
        cfg["cidade"] = a.cidade
    if a.min_seguidores is not None:
        cfg["min_seguidores"] = a.min_seguidores
    cfg.setdefault("min_seguidores", MIN_SEGUIDORES)
    if not cfg.get("eu"):
        sair("diga primeiro o seu perfil: perfil --eu @seuperfil")
    cfg["concorrentes"] = [c for c in cfg.get("concorrentes", []) if c != cfg["eu"]]
    gravar_config(cfg)
    mostrar({"configuracao": cfg, "arquivo": str(BASE / cfg["eu"] / "config.json"),
             "falta": [k for k in ("publico",) if not cfg.get(k)]})
    return 0


def cmd_ler_perfil(a) -> int:
    alvo = limpa(a.perfil) if a.perfil else config().get("eu")
    if not alvo:
        sair("diga qual perfil ler, ou rode antes: perfil --eu @seuperfil")
    dados = apify(PERFIS, {"usernames": [alvo]}, teto_usd=0.05)
    if not dados:
        sair(f"o Apify não achou o perfil @{alvo}")
    x = dados[0]
    posts = [{"legenda": " ".join((p.get("caption") or "").split())[:300], "curtidas": p.get("likesCount"),
              "comentarios": p.get("commentsCount"), "link": p.get("url")} for p in (x.get("latestPosts") or [])[:12]]
    mostrar({"perfil": alvo, "nome": x.get("fullName"), "seguidores": x.get("followersCount"),
             "posts": x.get("postsCount"), "bio": x.get("biography"), "categoria": x.get("businessCategoryName"),
             "privado": x.get("private"), "posts_recentes": posts})
    return 0


# ---------------------------------------------------------------- coleta

def contas_alvo(a, cfg: dict) -> list[tuple[str, str]]:
    contas = []
    if not a.so_concorrentes:
        contas.append((cfg["eu"], "eu"))
    if not a.so_eu:
        contas += [(c, "concorrente") for c in cfg.get("concorrentes", [])]
    if not contas:
        sair("nenhuma conta para ler. Confira o perfil e os concorrentes.")
    return contas


TETO_MINIMO = 0.05  # o Apify recebe no mínimo esse teto por chamada


def tetos(a, n_contas: int) -> dict:
    """Teto de gasto de cada chamada da coleta. O coletar usa estes mesmos valores (com folga de 50%)."""
    posts = n_contas * a.posts
    return {
        "posts": n_contas * (a.posts + 3) * PRECO[POSTS] * 1.5,
        "comentarios": posts * a.comentarios * PRECO[ENGAJAMENTO] * 1.5 if a.comentarios > 0 else 0,
        "curtidas": posts * a.curtidas * PRECO[ENGAJAMENTO] * 1.5 if a.curtidas > 0 else 0,
        "conferir_perfis": a.max_perfis * PRECO[PERFIS] * 1.5,
    }


def estimativa(a, n_contas: int) -> dict:
    posts = n_contas * a.posts
    engaj = posts * (a.curtidas + a.comentarios)
    t = tetos(a, n_contas)
    provavel = sum(v / 1.5 for v in t.values())
    teto = sum(max(v, TETO_MINIMO) for v in t.values() if v > 0)
    return {"contas": n_contas, "posts_lidos": posts, "interacoes_maximas": engaj,
            "perfis_conferidos_no_maximo": a.max_perfis,
            "custo_provavel_usd": round(provavel, 2), "teto_usd": round(teto, 2),
            "explicacao": "custo_provavel_usd: se todos os posts tiverem curtidas e comentários até o limite. "
                          "teto_usd: o máximo que o script deixa o Apify cobrar nesta rodada, somando as 4 chamadas."}


def cmd_estimar(a) -> int:
    cfg = config()
    pasta_do_perfil(cfg)
    contas = contas_alvo(a, cfg)
    est = estimativa(a, len(contas))
    est["contas_lidas"] = [f"@{c} ({t})" for c, t in contas]
    mostrar(est)
    return 0


def nao_e_paciente(x: dict) -> str | None:
    texto = " ".join(str(x.get(k) or "") for k in ("username", "fullName", "biography", "businessCategoryName")).lower()
    for padrao in NAO_PACIENTE:
        m = re.search(padrao, texto)
        if m:
            return f"vende na mesma área, ou é marca ou negócio (\"{m.group(0).strip()}\")"
    return None


def avaliar(x: dict, interacoes: list[dict], cfg: dict) -> tuple[int, list[str], str | None]:
    """Nota de 0 a 10 e motivo de descarte (ou None)."""
    seg = x.get("followersCount") or 0
    minimo = cfg.get("min_seguidores", MIN_SEGUIDORES)
    if seg <= minimo:
        return 0, [], f"{minimo} seguidores ou menos ({seg})"
    fora = nao_e_paciente(x)
    if fora:
        return 0, [], fora
    melhor = max(CALOR[(i["lado"], i["tipo"])] for i in interacoes)
    nota, motivos = melhor, []
    texto = " ".join(str(x.get(k) or "") for k in ("fullName", "biography", "businessCategoryName")).lower()
    for padrao in REVISAR:
        m = re.search(padrao, texto)
        if m:
            nota -= 1
            motivos.append(f"CONFIRA: a bio cita \"{m.group(0)}\" (profissional de outra área fica; negócio sai)")
    if x.get("verified"):
        nota -= 1
        motivos.append("CONFIRA: conta verificada (pessoa fica; marca sai)")
    if seg > MAX_SEGUIDORES:
        nota -= 1
        motivos.append(f"CONFIRA: mais de {MAX_SEGUIDORES // 1000} mil seguidores (pode ser influenciador)")
    tipos = sorted({f"{i['tipo']} em @{i['conta']}" for i in interacoes})
    motivos.append(", ".join(tipos))
    if len(interacoes) > 1:
        nota += 1
        motivos.append(f"{len(interacoes)} interações")
    bio = (x.get("biography") or "").lower()
    achou = [p for p in cfg.get("palavras", []) if p and p in bio]
    if achou:
        nota += min(2, len(achou))
        motivos.append("bio com " + ", ".join(achou[:3]))
    if cfg.get("cidade") and cfg["cidade"].lower() in bio:
        nota += 1
        motivos.append(f"cidade: {cfg['cidade']}")
    if not bio.strip():
        nota -= 2
        motivos.append("bio vazia")
    if x.get("private"):
        nota -= 1
        motivos.append("perfil fechado (bio visível, posts não)")
    return max(0, min(10, nota)), motivos, None


def grupo(f: dict) -> int:
    """Ordem de envio: comentou no seu > curtiu no seu > comentou em concorrente > curtiu em concorrente."""
    return max(CALOR[(i["lado"], i["tipo"])] for i in f["interacoes"])


def para_registro(ficha: dict) -> dict:
    """O registro guarda só o necessário: o comentário da pessoa fica no arquivo da rodada."""
    r = dict(ficha)
    r["interacoes"] = [{k: i[k] for k in ("tipo", "conta", "lado", "post", "legenda_do_post")} for i in ficha["interacoes"]]
    return r


def cmd_coletar(a) -> int:
    cfg = config()
    pasta = pasta_do_perfil(cfg)
    contas = contas_alvo(a, cfg)
    est = estimativa(a, len(contas))
    reg = ler_json(pasta / "registro.json", {})
    momento = agora()

    # 1. Posts recentes de cada conta (pula fixados e posts sem interação).
    t = tetos(a, len(contas))
    brutos = apify(POSTS, {"username": [c for c, _ in contas], "resultsLimit": a.posts + 3}, teto_usd=t["posts"])
    lado = {c: t for c, t in contas}
    escolhidos: dict[str, list[dict]] = {c: [] for c, _ in contas}
    for p in sorted(brutos, key=lambda p: p.get("timestamp") or "", reverse=True):
        dono = (p.get("ownerUsername") or "").lower()
        if dono in escolhidos and not p.get("isPinned") and len(escolhidos[dono]) < a.posts \
                and ((p.get("likesCount") or 0) + (p.get("commentsCount") or 0)) > 0:
            escolhidos[dono].append(p)
    posts = {p["url"].rstrip("/"): {"conta": d, "lado": lado[d], "legenda": " ".join((p.get("caption") or "").split())[:160]}
             for d, ps in escolhidos.items() for p in ps}
    sem_posts = [c for c, ps in escolhidos.items() if not ps]
    if not posts:
        sair("nenhum post com interação nas contas lidas (perfis fechados ou sem posts?): " + ", ".join(sem_posts))

    # 2. Quem curtiu e quem comentou.
    urls = list(posts)
    interacoes: list[dict] = []
    for tipo, limite, chave in (("comentou", a.comentarios, "comments"), ("curtiu", a.curtidas, "likes")):
        if limite <= 0:
            continue
        teto = min(t["comentarios" if chave == "comments" else "curtidas"], len(urls) * limite * PRECO[ENGAJAMENTO] * 1.5)
        for x in apify(ENGAJAMENTO, {"Posts": [u + "/" for u in urls], "resultsLimit": limite, "dataToScrape": chave}, teto):
            user = (x.get("user.username") or "").lower()
            info = posts.get((x.get("link_post") or "").rstrip("/"))
            if not user or not info:
                continue
            interacoes.append({"perfil": user, "tipo": tipo, "conta": info["conta"], "lado": info["lado"],
                               "post": (x.get("link_post") or "").rstrip("/") + "/", "legenda_do_post": info["legenda"],
                               "comentario": (x.get("text") or "")[:300] if tipo == "comentou" else "",
                               "privado": x.get("user.is_private"), "verificado": x.get("user.is_verified"),
                               "nome": x.get("user.full_name") or ""})

    # 3. Pessoas novas: tira as próprias contas lidas e quem já está no registro.
    lidas = {c for c, _ in contas}
    por_pessoa: dict[str, list[dict]] = {}
    for i in interacoes:
        if i["perfil"] in lidas:
            continue
        por_pessoa.setdefault(i["perfil"], []).append(i)
    pessoas_desta_coleta = len(por_pessoa)
    # Quem não coube no limite da rodada anterior volta para a fila (se ainda não está no registro).
    fila_antiga = ler_json(pasta / "fila.json", {})
    da_fila = 0
    for p, its in fila_antiga.items():
        if p not in reg and p not in lidas and p not in por_pessoa:
            por_pessoa[p] = its
            da_fila += 1
    # Quem foi conferido antes e ainda não recebeu mensagem pronta (etapa "visto") continua disponível.
    vistos = {p: f for p, f in reg.items() if f.get("etapa") == "visto"}
    ja_no_registro = sorted(p for p in por_pessoa if p in reg and p not in vistos)
    novos = {p: its for p, its in por_pessoa.items() if p not in reg}
    # Perfil fechado mostra bio e seguidores: é conferido, só que depois dos abertos de mesmo calor.
    fila = sorted(novos, key=lambda p: (-max(CALOR[(i["lado"], i["tipo"])] for i in novos[p]),
                                        bool(novos[p][0]["privado"]), -len(novos[p])))
    conferir, sobra = fila[:a.max_perfis], fila[a.max_perfis:]

    # 4. Conferir seguidores e bio de quem sobrou.
    achados = {}
    if conferir:
        for x in apify(PERFIS, {"usernames": conferir}, teto_usd=len(conferir) * PRECO[PERFIS] * 1.5):
            if x.get("username"):
                achados[x["username"].lower()] = x

    stamp = momento.strftime("%Y-%m-%d_%Hh%M")
    rodada = pasta / "rodadas" / stamp
    leads, descartados = [], []
    for p in conferir:
        its = novos[p]
        x = achados.get(p)
        if not x:
            continue
        nota, motivos, fora = avaliar(x, its, cfg)
        ficha = {
            "perfil": p, "link": f"https://www.instagram.com/{p}/", "nome": (x.get("fullName") or "").strip(),
            "seguidores": x.get("followersCount"), "posts": x.get("postsCount"),
            "bio": " ".join((x.get("biography") or "").split())[:400],
            "origem": "seu perfil" if any(i["lado"] == "eu" for i in its) else "concorrente",
            "interacoes": [{k: i[k] for k in ("tipo", "conta", "lado", "post", "legenda_do_post", "comentario")} for i in its],
            "privado": bool(x.get("private")), "verificado": bool(x.get("verified")),
            "nota": nota, "motivos": motivos, "etapa": "descartado" if fora else "visto", "obs": fora or "",
            "visto_em": hoje(), "rodada": stamp,
        }
        reg[p] = para_registro(ficha)
        (descartados if fora else leads).append(ficha)

    # Vistos de rodadas anteriores: voltam à lista sem gastar crédito, com as interações novas somadas.
    anteriores = 0
    for p, f in vistos.items():
        its = list(f.get("interacoes") or [])
        for i in por_pessoa.get(p, []):
            if not any(j["post"] == i["post"] and j["tipo"] == i["tipo"] for j in its):
                its.append({k: i.get(k, "") for k in ("tipo", "conta", "lado", "post", "legenda_do_post", "comentario")})
        if not its:
            continue
        x = {"username": p, "fullName": f.get("nome"), "followersCount": f.get("seguidores"), "biography": f.get("bio"),
             "private": f.get("privado"), "verified": f.get("verificado")}
        nota, motivos, fora = avaliar(x, its, cfg)
        ficha = {**f, "interacoes": [{**{"comentario": ""}, **i} for i in its], "nota": nota, "motivos": motivos,
                 "origem": "seu perfil" if any(i["lado"] == "eu" for i in its) else "concorrente", "rodada": stamp,
                 "de_rodada_anterior": True}
        if fora:
            ficha.update(etapa="descartado", obs=fora)
            descartados.append(ficha)
        else:
            leads.append(ficha)
            anteriores += 1
        reg[p] = para_registro(ficha)
    leads.sort(key=lambda f: (-grupo(f), -f["nota"], -(f["seguidores"] or 0)))
    gravar_json(pasta / "registro.json", reg)
    gravar_json(pasta / "fila.json", {p: novos[p] for p in sobra})

    funil = {
        "interacoes_lidas": len(interacoes), "pessoas_unicas": pessoas_desta_coleta,
        "vieram_da_fila_da_rodada_anterior": da_fila, "ja_estavam_no_registro": len(ja_no_registro),
        "conferidas": len(achados), "ficaram_na_fila_para_a_proxima_rodada": len(sobra),
        "vistos_antes_sem_mensagem": anteriores, "passaram_no_filtro": len(leads),
    }
    motivos_descarte: dict[str, int] = {}
    for d in descartados:
        chave = re.sub(r' \((\d+|"[^"]*")\)$', "", d["obs"])
        motivos_descarte[chave] = motivos_descarte.get(chave, 0) + 1
    resumo = {"rodada": stamp, "pasta": str(rodada), "perfil": cfg["eu"], "contas_lidas": [f"@{c}" for c in lidas],
              "contas_sem_posts": sem_posts, "posts_lidos": len(posts), "funil": funil,
              "descartes_por_motivo": motivos_descarte, "teto_de_custo_usd": est["teto_usd"],
              "configuracao": {k: cfg.get(k) for k in ("publico", "palavras", "cidade", "min_seguidores")}}
    gravar_json(rodada / "rodada.json", {**resumo, "leads": leads, "descartados": descartados})
    mostrar({**resumo, "leads": [{k: f.get(k) for k in ("perfil", "nome", "seguidores", "origem", "nota", "motivos", "bio", "privado")}
                                  | {"o_que_fez": [f"{i['tipo']} em @{i['conta']}" + (f": \"{i['comentario']}\"" if i["comentario"] else "")
                                                   + (f" (post: {i['legenda_do_post'][:80]})" if i["lado"] == "eu" else "")
                                                   for i in f["interacoes"]]}
                                  for f in leads]})
    return 0


# ---------------------------------------------------------------- relatório

def achar_rodada(nome: str) -> Path:
    raiz = pasta_do_perfil() / "rodadas"
    if nome == "ultima":
        todas = sorted(p for p in raiz.glob("*") if (p / "rodada.json").is_file()) if raiz.is_dir() else []
        if not todas:
            sair("nenhuma rodada coletada ainda. Rode: coletar")
        return todas[-1]
    p = Path(nome) if Path(nome).is_dir() else raiz / nome
    if not (p / "rodada.json").is_file():
        sair(f"não achei a rodada {nome}")
    return p


def cmd_relatorio(a) -> int:
    import relatorio  # noqa: E402  (scripts/relatorio.py)

    rodada = achar_rodada(a.rodada)
    dados = json.loads((rodada / "rodada.json").read_text(encoding="utf-8"))
    cfg = config()
    if dados.get("perfil") != cfg.get("eu"):
        sair(f"esta rodada é de @{dados.get('perfil')}, e o perfil ativo é @{cfg.get('eu')}. Rode: perfil --eu @{dados.get('perfil')}")
    reg = ler_json(registro_path(), {})
    msgs = json.loads(Path(a.mensagens).read_text(encoding="utf-8"))
    msgs = {limpa(k): v for k, v in msgs.items()}
    por_perfil = {f["perfil"]: f for f in dados["leads"]}
    faltam = [p for p in msgs if p not in por_perfil]
    if faltam:
        sair("estes perfis não estão entre os leads da rodada: " + ", ".join(faltam))
    erros = []
    escolhidos = []
    concorrentes = [c for c in cfg.get("concorrentes", []) if c]
    for p, m in msgs.items():
        etapa = reg.get(p, {}).get("etapa")
        mesma_rodada = etapa == "sugerido" and reg[p].get("sugerido_na_rodada") == rodada.name
        if etapa != "visto" and not mesma_rodada:
            erros.append(f"@{p}: já está como \"{etapa}\" no registro; não entra numa lista nova")
            continue
        partes = m.get("partes") if isinstance(m, dict) else m
        if not isinstance(partes, list) or len(partes) != 4 or not all(isinstance(t, str) and t.strip() for t in partes):
            erros.append(f"@{p}: a mensagem precisa ter as 4 partes (nome e hora, motivo, relacionamento, dia e tchau)")
            continue
        texto = "\n".join(t.strip() for t in partes)
        for regra, achou in relatorio.conferir_mensagem(texto) + relatorio.conferir_partes(partes):
            erros.append(f"@{p}: {regra} ({achou})")
        citado = [c for c in concorrentes if c in texto.lower().replace("@", "")]
        if citado:
            erros.append(f"@{p}: a mensagem cita o concorrente @{citado[0]}; o motivo sai do perfil da pessoa")
        lead = dict(por_perfil[p])
        lead["partes"] = [t.strip() for t in partes]
        lead["mensagem"] = texto
        lead["porque"] = (m.get("porque") if isinstance(m, dict) else "") or "; ".join(lead["motivos"])
        escolhidos.append(lead)
    if erros:
        print(json.dumps({"mensagens_com_problema": erros}, ensure_ascii=False, indent=1))
        sair("corrija as mensagens e rode de novo (nada foi gerado).")
    ordem = {f["perfil"]: n for n, f in enumerate(dados["leads"])}
    escolhidos.sort(key=lambda l: ordem[l["perfil"]])
    xlsx = rodada / f"prospeccao-{cfg['eu']}-{rodada.name}.xlsx"
    html = rodada / f"painel-{cfg['eu']}-{rodada.name}.html"
    futuro = json.loads(json.dumps(reg))
    for lead in escolhidos:
        futuro[lead["perfil"]].update(etapa="sugerido", sugerido_em=futuro[lead["perfil"]].get("sugerido_em") or hoje(),
                                      sugerido_na_rodada=rodada.name)
    relatorio.planilha(xlsx, dados, escolhidos, futuro, cfg)
    relatorio.painel(html, dados, escolhidos, cfg)
    gravar_json(registro_path(), futuro)  # só depois que os dois arquivos existem
    mostrar({"planilha": str(xlsx), "painel": str(html), "leads_na_lista": len(escolhidos)})
    return 0


# ---------------------------------------------------------------- acompanhamento

def cmd_marcar(a) -> int:
    reg = ler_json(registro_path(), {})
    faltam, feitos = [], 0
    for p in map(limpa, a.perfis):
        if p not in reg:
            faltam.append(p)
            continue
        reg[p]["etapa"] = a.status
        reg[p][a.status.replace("-", "_") + "_em"] = hoje()
        if a.obs:
            reg[p]["obs"] = (reg[p].get("obs", "") + " | " + a.obs).strip(" |")
        feitos += 1
    gravar_json(registro_path(), reg)
    print(f"ok: {feitos} marcado(s) como {a.status}")
    if faltam:
        print("Não estão no registro: " + ", ".join(faltam), file=sys.stderr)
        return 1
    return 0


def cmd_pendentes(a) -> int:
    reg = ler_json(registro_path(), {})
    d = lambda n: (agora() - timedelta(days=n)).strftime("%Y-%m-%d")
    campos = lambda f: {k: f.get(k) for k in ("perfil", "link", "nome", "origem", "abordado_em", "segundo_toque_em", "obs")}
    mostrar({
        "interagir_no_conteudo_hoje": [campos(f) for f in reg.values()
                                       if f["etapa"] == "abordado" and f.get("abordado_em", "9") <= d(3)],
        "encerrar": [campos(f) for f in reg.values()
                     if f["etapa"] == "segundo-toque" and f.get("segundo_toque_em", "9") <= d(7)],
        "sugeridos_sem_retorno": [campos(f) for f in reg.values() if f["etapa"] == "sugerido"],
    })
    return 0


def cmd_resumo(a) -> int:
    reg = ler_json(registro_path(), {})
    corte = (agora() - timedelta(days=a.dias)).strftime("%Y-%m-%d")
    por_origem: dict[str, dict] = {}
    for f in reg.values():
        if not f.get("abordado_em") or f["abordado_em"] < corte:
            continue
        linha = por_origem.setdefault(f.get("origem") or "?", {"abordados": 0, "responderam": 0, "viraram_paciente": 0})
        linha["abordados"] += 1
        if f.get("respondeu_em") or f.get("virou_paciente_em") or f["etapa"] in ("respondeu", "virou-paciente"):
            linha["responderam"] += 1
        if f.get("virou_paciente_em") or f["etapa"] == "virou-paciente":
            linha["viraram_paciente"] += 1
    for linha in por_origem.values():
        linha["taxa_de_resposta"] = f"{100 * linha['responderam'] / linha['abordados']:.0f}%"
    mostrar({"periodo_dias": a.dias, "por_origem": por_origem,
             "registro_por_etapa": {e: sum(1 for f in reg.values() if f["etapa"] == e) for e in ETAPAS}})
    return 0


# ---------------------------------------------------------------- linha de comando

def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("configurar")
    s.add_argument("--nao-abrir", action="store_true")
    s.set_defaults(f=cmd_configurar)
    sub.add_parser("status").set_defaults(f=cmd_status)
    s = sub.add_parser("perfil")
    s.add_argument("--eu")
    s.add_argument("--concorrentes", nargs="*", help="soma aos três padrão (use --sem-padrao para trocar)")
    s.add_argument("--sem-padrao", action="store_true")
    s.add_argument("--tirar", nargs="*")
    s.add_argument("--publico")
    s.add_argument("--palavras", help="palavras do público na bio, separadas por vírgula")
    s.add_argument("--cidade")
    s.add_argument("--min-seguidores", type=int)
    s.set_defaults(f=cmd_perfil)
    s = sub.add_parser("ler-perfil")
    s.add_argument("perfil", nargs="?")
    s.set_defaults(f=cmd_ler_perfil)
    for nome, func in (("estimar", cmd_estimar), ("coletar", cmd_coletar)):
        s = sub.add_parser(nome)
        s.add_argument("--posts", type=int, default=2, help="posts recentes por conta (padrão 2)")
        s.add_argument("--curtidas", type=int, default=60, help="curtidas lidas por post (padrão 60)")
        s.add_argument("--comentarios", type=int, default=40, help="comentários lidos por post (padrão 40)")
        s.add_argument("--max-perfis", type=int, default=120, help="pessoas conferidas no máximo (padrão 120)")
        s.add_argument("--so-eu", action="store_true")
        s.add_argument("--so-concorrentes", action="store_true")
        s.set_defaults(f=func)
    s = sub.add_parser("relatorio")
    s.add_argument("--mensagens", required=True, help="JSON {\"@perfil\": {\"partes\": [4 textos], \"porque\": \"...\"}}")
    s.add_argument("--rodada", default="ultima")
    s.set_defaults(f=cmd_relatorio)
    s = sub.add_parser("marcar")
    s.add_argument("perfis", nargs="+")
    s.add_argument("--status", required=True, choices=ETAPAS)
    s.add_argument("--obs")
    s.set_defaults(f=cmd_marcar)
    sub.add_parser("pendentes").set_defaults(f=cmd_pendentes)
    s = sub.add_parser("resumo")
    s.add_argument("--dias", type=int, default=30)
    s.set_defaults(f=cmd_resumo)
    a = ap.parse_args()
    try:
        return a.f(a)
    except PermissionError as e:
        sair(f"não consegui gravar em {e.filename}. No Codex, o sandbox padrão só deixa gravar na pasta de trabalho: "
             "rode o comando de novo pedindo permissão para sair do sandbox.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
