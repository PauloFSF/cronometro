"""Testes do cronometro.html com Playwright (Chromium headless).

Uso, da pasta do repositorio:
    uv run --no-project --with playwright==1.65.1 python testes/testar.py
    uv run --no-project --with playwright==1.65.1 python testes/testar.py --mutacao

--html CAMINHO    testa outro arquivo (padrao: cronometro.html ao lado da pasta testes)
--mutacao         depois da bateria normal, gera uma copia quebrada do fim do tempo
                  (troca "<= 0" por "< 0") e confere que a bateria REPROVA
--sem-relatorio   nao grava testes/RESULTADO.md

Grava o detalhe em testes/log/resultado.json e o resumo em testes/RESULTADO.md.
Sai com codigo 1 se algum teste falhar (ou se o mutante passar).
"""
import argparse
import datetime
import json
import math
import struct
import sys
import time
import traceback
import wave
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

PASTA_TESTES = Path(__file__).resolve().parent
RAIZ = PASTA_TESTES.parent
LOG = PASTA_TESTES / "log"
LOG.mkdir(exist_ok=True)

TRECHO_FIM = "restante(agora) <= 0"
TRECHO_MUTANTE = "restante(agora) < 0"


class Falha(Exception):
    pass


def conferir(cond, msg):
    if not cond:
        raise Falha(msg)


def gerar_wav(caminho, segundos=0.5, freq=440.0, taxa=22050):
    with wave.open(str(caminho), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taxa)
        quadros = b"".join(
            struct.pack("<h", int(12000 * math.sin(2 * math.pi * freq * i / taxa)))
            for i in range(int(taxa * segundos))
        )
        w.writeframes(quadros)


class Sessao:
    """Um contexto novo (armazenamento limpo) com uma pagina aberta no arquivo."""

    def __init__(self, browser, url, largura=900, altura=900):
        self.ctx = browser.new_context(viewport={"width": largura, "height": altura})
        self.ctx.add_init_script(
            "window.__notif = 0;"
            "if (window.Notification) { const r = Notification.requestPermission;"
            " Notification.requestPermission = function () { window.__notif++; return r.apply(this, arguments); }; }"
        )
        self.page = self.ctx.new_page()
        self.erros, self.pedidos = [], []
        self.page.on("pageerror", lambda e: self.erros.append("pageerror: " + str(e)))
        self.page.on("console", lambda m: self.erros.append("console: " + m.text) if m.type == "error" else None)
        self.page.on("request", lambda r: self.pedidos.append(r.url))
        self.url = url
        self.abrir()

    def abrir(self):
        self.page.goto(self.url)
        self.page.wait_for_function("window.cronometro !== undefined")

    def recarregar(self):
        self.page.reload()
        self.page.wait_for_function("window.cronometro !== undefined")

    def js(self, expr):
        return self.page.evaluate(expr)

    def estado(self):
        return self.js("cronometro.estado()")

    def som(self):
        return self.js("cronometro.som()")

    def definir(self, m, s):
        self.page.fill("#minutos", str(m))
        self.page.fill("#segundos", str(s))
        self.page.locator("#segundos").blur()

    def esperar_estado(self, nome, timeout=8000):
        self.page.wait_for_function(f"cronometro.estado() === '{nome}'", polling=5, timeout=timeout)

    def fechar(self):
        self.ctx.close()


# ---------------- testes ----------------

def t_contagem_3s(b, url):
    s = Sessao(b, url)
    s.definir(0, 3)
    p0 = s.js("performance.now()")
    t0 = time.perf_counter()
    s.page.click("#principal")
    titulo = s.page.title()
    s.esperar_estado("tocando", timeout=6000)
    t1 = time.perf_counter()
    dentro = s.js("cronometro.instantes.fim") - p0
    medido = t1 - t0
    som = s.som()
    titulo_fim = s.page.title()
    pulsa = s.js("document.body.classList.contains('tocando')")
    conferir(2.9 <= medido <= 3.3, f"durou {medido:.3f} s (fora de 2,9 a 3,3)")
    conferir(titulo.startswith("00:0") and "Cronômetro" in titulo, f"titulo rodando: {titulo!r}")
    conferir(som["tocando"] and som["loop"], f"som no fim: {som}")
    conferir(som["contexto"] == "running", f"AudioContext: {som['contexto']}")
    conferir(pulsa, "sinal visual (classe tocando) nao apareceu")
    time.sleep(1.6)  # o loop continua depois de uma volta inteira do beep (1,4 s)
    som_depois = s.som()
    conferir(som_depois["tocando"], "som parou sozinho antes de clicar em Parar som")
    s.page.click("#pararSom")
    som_parado = s.som()
    conferir(not som_parado["tocando"], f"Parar som nao parou: {som_parado}")
    conferir(s.estado() == "parado", "nao voltou ao estado parado")
    s.fechar()
    return {
        "duracao_relogio_do_teste_s": round(medido, 3),
        "duracao_dentro_da_pagina_ms": round(dentro, 1),
        "titulo_rodando": titulo,
        "titulo_fim": titulo_fim,
        "som_no_fim": som,
        "som_1_6s_depois": som_depois["tocando"],
        "som_apos_parar": som_parado["tocando"],
    }, s.erros


def t_qualquer_tecla_para(b, url):
    s = Sessao(b, url)
    s.definir(0, 1)
    s.page.click("#principal")
    s.esperar_estado("tocando", timeout=4000)
    antes = s.som()["tocando"]
    s.page.keyboard.press("a")
    depois = s.som()["tocando"]
    conferir(antes and not depois, f"tecla 'a': antes={antes} depois={depois}")
    s.fechar()
    return {"tocando_antes": antes, "tocando_depois_da_tecla_a": depois}, s.erros


def t_pausar_continuar(b, url):
    s = Sessao(b, url)
    s.definir(0, 10)
    s.page.click("#principal")
    icones = [s.page.is_visible("#iconePlay"), s.page.is_visible("#iconePausa"), s.page.inner_text("#rotuloPrincipal")]
    conferir(icones == [False, True, "Pausar"], f"icone rodando (play, pausa, rotulo): {icones}")
    time.sleep(1.2)
    s.page.click("#principal")  # pausar
    icones_p = [s.page.is_visible("#iconePlay"), s.page.is_visible("#iconePausa"), s.page.inner_text("#rotuloPrincipal")]
    conferir(icones_p == [True, False, "Continuar"], f"icone pausado (play, pausa, rotulo): {icones_p}")
    conferir(s.estado() == "pausado", "nao pausou")
    txt1, r1 = s.page.inner_text("#numero"), s.js("cronometro.restanteMs()")
    time.sleep(1.5)
    txt2, r2 = s.page.inner_text("#numero"), s.js("cronometro.restanteMs()")
    conferir(txt1 == txt2 and r1 == r2, f"pausado mudou: {txt1}/{r1} -> {txt2}/{r2}")
    s.page.click("#principal")  # continuar
    conferir(s.estado() == "rodando", "nao continuou")
    time.sleep(1.1)
    r3 = s.js("cronometro.restanteMs()")
    andou = r1 - r3
    conferir(900 <= andou <= 1400, f"depois de continuar andou {andou:.0f} ms em 1,1 s")
    s.fechar()
    return {"icone_rodando_play_pausa_rotulo": icones, "icone_pausado": icones_p, "display_pausado": txt1, "restante_pausado_ms": round(r1, 1),
            "restante_1_5s_depois_ms": round(r2, 1), "andou_1_1s_apos_continuar_ms": round(andou, 1)}, s.erros


def t_zerar(b, url):
    s = Sessao(b, url)
    s.definir(1, 30)
    s.page.click("#principal")
    time.sleep(1.2)
    s.page.click("#zerar")
    v1 = (s.page.input_value("#minutos"), s.page.input_value("#segundos"), s.estado())
    conferir(v1 == ("01", "30", "parado"), f"botao Zerar: {v1}")
    s.page.click("#principal")
    time.sleep(0.5)
    s.page.keyboard.press("Escape")
    v2 = (s.page.input_value("#minutos"), s.page.input_value("#segundos"), s.estado())
    conferir(v2 == ("01", "30", "parado"), f"Esc: {v2}")
    s.fechar()
    return {"apos_botao_zerar": v1, "apos_esc": v2}, s.erros


def t_tecla_espaco(b, url):
    s = Sessao(b, url)
    s.definir(0, 20)
    s.page.click("h1")
    seq = []
    for _ in range(3):
        s.page.keyboard.press("Space")
        seq.append(s.estado())
    conferir(seq == ["rodando", "pausado", "rodando"], f"Espaco: {seq}")
    s.page.keyboard.press("Escape")
    # foco no botao principal: Espaco nao pode acionar duas vezes (atalho + clique do botao)
    s.page.focus("#principal")
    s.page.keyboard.press("Space")
    time.sleep(0.2)
    com_foco = s.estado()
    conferir(com_foco == "rodando", f"Espaco com foco no botao deu {com_foco}")
    s.fechar()
    return {"sequencia": seq, "espaco_com_foco_no_botao": com_foco}, s.erros


def t_negativos(b, url):
    s = Sessao(b, url)
    r = {}
    s.definir(0, 0)
    r["iniciar_desabilitado_em_00_00"] = s.js("document.getElementById('principal').disabled")
    s.page.click("h1")
    s.page.keyboard.press("Space")
    r["estado_apos_espaco_em_00_00"] = s.estado()
    conferir(r["iniciar_desabilitado_em_00_00"], "Iniciar habilitado com 00:00")
    conferir(r["estado_apos_espaco_em_00_00"] == "parado", "00:00 iniciou pelo Espaco")
    s.page.fill("#minutos", "")
    s.page.locator("#minutos").press_sequentially("ab")
    r["digitar_ab"] = s.page.input_value("#minutos")
    s.page.fill("#minutos", "")
    s.page.locator("#minutos").press_sequentially("-5")
    r["digitar_-5"] = s.page.input_value("#minutos")
    s.page.fill("#minutos", "-3")  # colar
    r["colar_-3"] = s.page.input_value("#minutos")
    conferir(r["digitar_ab"] == "", f"letras entraram: {r['digitar_ab']!r}")
    conferir(r["digitar_-5"] == "5", f"sinal entrou: {r['digitar_-5']!r}")
    conferir(r["colar_-3"] == "3", f"sinal colado entrou: {r['colar_-3']!r}")
    s.definir(0, 75)
    r["0_min_75_s"] = s.page.input_value("#minutos") + ":" + s.page.input_value("#segundos")
    s.definir(2, 99)
    r["2_min_99_s"] = s.page.input_value("#minutos") + ":" + s.page.input_value("#segundos")
    conferir(r["0_min_75_s"] == "01:15", f"75 s virou {r['0_min_75_s']}")
    conferir(r["2_min_99_s"] == "03:39", f"2 min 99 s virou {r['2_min_99_s']}")
    s.fechar()
    return r, s.erros


def t_horas_e_atalhos(b, url):
    s = Sessao(b, url)
    s.page.click("button[data-min='25']")
    atalho = s.page.input_value("#minutos") + ":" + s.page.input_value("#segundos")
    conferir(atalho == "25:00", f"atalho 25 deu {atalho}")
    s.definir(90, 0)
    s.page.click("#principal")
    txt = s.page.inner_text("#numero")
    conferir(txt in ("1:30:00", "1:29:59"), f"90 min mostrou {txt}")
    atalho_rodando = s.js("document.querySelector(\"button[data-min='5']\").disabled")
    conferir(atalho_rodando, "atalho ficou ativo com o tempo rodando")
    s.fechar()
    return {"atalho_25": atalho, "display_90_min": txt, "atalho_desabilitado_rodando": atalho_rodando}, s.erros


def t_relogio_real_pagina_congelada(b, url):
    """Congela a pagina 2 s (como o navegador faz com aba em segundo plano).
    Somando intervalos, o fim atrasaria 2 s; pelo relogio, nao atrasa."""
    s = Sessao(b, url)
    cdp = s.ctx.new_cdp_session(s.page)
    s.definir(0, 4)
    t0 = time.perf_counter()
    s.page.click("#principal")
    time.sleep(0.5)
    cdp.send("Page.setWebLifecycleState", {"state": "frozen"})
    time.sleep(2.0)
    cdp.send("Page.setWebLifecycleState", {"state": "active"})
    t_volta = time.perf_counter() - t0
    restante_ms = s.js("cronometro.restanteMs()")
    s.esperar_estado("tocando", timeout=8000)
    total = time.perf_counter() - t0
    esperado = 4000 - t_volta * 1000
    conferir(abs(restante_ms - esperado) < 300, f"ao voltar restavam {restante_ms:.0f} ms, esperado ~{esperado:.0f}")
    conferir(3.9 <= total <= 4.4, f"fim em {total:.3f} s (esperado 4 s)")
    s.page.click("#pararSom")
    s.fechar()
    return {"voltou_em_s": round(t_volta, 3), "restante_ao_voltar_ms": round(restante_ms, 1),
            "esperado_ms": round(esperado, 1), "fim_em_s": round(total, 3)}, s.erros


def t_persistencia_som(b, url):
    wav = LOG / "teste_440hz.wav"
    gerar_wav(wav)
    falso = LOG / "nao_e_audio.wav"
    falso.write_text("isto nao e audio", encoding="utf-8")
    s = Sessao(b, url)
    r = {"wav_bytes": wav.stat().st_size}

    s.page.set_input_files("#arquivo", str(falso))
    s.page.wait_for_selector("#erroSom:not([hidden])", timeout=4000)
    r["arquivo_invalido_erro"] = s.page.inner_text("#erroSom")
    r["arquivo_invalido_escolhido"] = s.som()["escolhido"]
    conferir(r["arquivo_invalido_escolhido"] == "beep", "arquivo invalido foi aceito")

    s.page.set_input_files("#arquivo", str(wav))
    s.page.wait_for_selector("#nomeSom:not([hidden])", timeout=4000)
    s.recarregar()
    s.page.wait_for_selector("#nomeSom:not([hidden])", timeout=4000)
    r["nome_apos_recarregar"] = s.page.inner_text("#nomeArquivo")
    r["select_apos_recarregar"] = s.page.input_value("#escolhaSom")
    r["blob_apos_recarregar"] = s.js("""new Promise(ok => { const q = indexedDB.open('cronometro');
        q.onsuccess = () => { const g = q.result.transaction('sons').objectStore('sons').get('personalizado');
        g.onsuccess = () => ok(g.result ? {nome: g.result.nome, bytes: g.result.blob.size, tipo: g.result.blob.type,
        eh_blob: g.result.blob instanceof Blob} : null); }; })""")
    conferir(r["nome_apos_recarregar"] == wav.name, f"nome: {r['nome_apos_recarregar']!r}")
    conferir(r["select_apos_recarregar"] == "personalizado", f"select: {r['select_apos_recarregar']}")
    blob = r["blob_apos_recarregar"]
    conferir(blob and blob["eh_blob"] and blob["bytes"] == r["wav_bytes"], f"blob: {blob}")

    s.page.click("#testar")
    s.page.wait_for_function("cronometro.som().tocando", timeout=3000)
    r["testar_tocando_loop"] = [s.som()["tocando"], s.som()["loop"]]
    conferir(r["testar_tocando_loop"] == [True, False], f"Testar: {r['testar_tocando_loop']}")
    s.page.wait_for_function("!cronometro.som().tocando", timeout=3000)  # 0,5 s e acaba sozinho

    s.definir(0, 1)
    s.page.click("#principal")
    s.esperar_estado("tocando", timeout=4000)
    s.page.wait_for_function("cronometro.som().tocando", timeout=3000)
    time.sleep(1.2)  # o arquivo tem 0,5 s; em loop continua tocando
    r["fim_com_meu_som_1_2s_depois"] = s.som()
    conferir(r["fim_com_meu_som_1_2s_depois"]["tocando"] and r["fim_com_meu_som_1_2s_depois"]["loop"],
             f"fim com meu som: {r['fim_com_meu_som_1_2s_depois']}")
    s.page.click("#pararSom")

    s.js("const v = document.getElementById('volume'); v.value = 30; v.dispatchEvent(new Event('input'))")
    s.recarregar()
    r["volume_apos_recarregar"] = s.page.input_value("#volume")
    conferir(r["volume_apos_recarregar"] == "30", f"volume: {r['volume_apos_recarregar']}")

    s.page.click("#padrao")
    s.page.wait_for_selector("#nomeSom", state="hidden", timeout=3000)
    s.recarregar()
    r["apos_padrao_select"] = s.page.input_value("#escolhaSom")
    r["apos_padrao_nome_visivel"] = s.page.is_visible("#nomeSom")
    r["apos_padrao_blob"] = s.js("""new Promise(ok => { const q = indexedDB.open('cronometro');
        q.onsuccess = () => { const g = q.result.transaction('sons').objectStore('sons').get('personalizado');
        g.onsuccess = () => ok(g.result === undefined ? null : 'ainda existe'); }; })""")
    conferir(r["apos_padrao_select"] == "beep" and not r["apos_padrao_nome_visivel"] and r["apos_padrao_blob"] is None,
             f"voltar ao padrao: {r['apos_padrao_select']}, {r['apos_padrao_nome_visivel']}, {r['apos_padrao_blob']}")
    s.fechar()
    # o erro de decodificacao do arquivo falso aparece no console do Chromium; nao e erro do programa
    erros = [e for e in s.erros if "decod" not in e.lower() and "unable to" not in e.lower()]
    return r, erros


def t_sons_embutidos(b, url):
    s = Sessao(b, url)
    r = {}
    for tipo in ("beep", "sino", "alarme"):
        r[tipo] = s.js(f"""sintetizar('{tipo}').then(buf => {{ const d = buf.getChannelData(0); let pico = 0, soma = 0;
            for (let i = 0; i < d.length; i++) {{ const a = Math.abs(d[i]); if (a > pico) pico = a; soma += d[i] * d[i]; }}
            return {{ duracao_s: +buf.duration.toFixed(3), pico: +pico.toFixed(3), rms: +Math.sqrt(soma / d.length).toFixed(4) }}; }})""")
        conferir(0.05 < r[tipo]["pico"] <= 1.0, f"{tipo}: pico {r[tipo]['pico']} (mudo ou estourado)")
        s.page.select_option("#escolhaSom", tipo)
        s.page.click("#testar")
        s.page.wait_for_function("cronometro.som().tocando", timeout=3000)
        r[tipo]["testar_tocou"] = True
        s.page.click("#testar")  # vira "Parar"
        conferir(not s.som()["tocando"], f"{tipo}: Parar do teste nao parou")
    s.fechar()
    return r, s.erros


def t_visual_e_isolamento(b, url):
    r = {}
    s = Sessao(b, url, largura=400, altura=860)
    r["largura_conteudo_em_400px"] = s.js("document.documentElement.scrollWidth")
    conferir(r["largura_conteudo_em_400px"] <= 400, f"rolagem horizontal em 400 px: {r['largura_conteudo_em_400px']}")
    s.page.screenshot(path=str(LOG / "tela_400px_parado.png"), full_page=True)
    s.definir(0, 1)
    s.page.click("#principal")
    s.esperar_estado("tocando", timeout=4000)
    time.sleep(0.5)
    s.page.screenshot(path=str(LOG / "tela_400px_tocando.png"), full_page=True)
    s.page.click("#pararSom")
    r["pedidos_fora_de_file"] = [u for u in s.pedidos if not u.startswith("file:")]
    r["pedidos_de_notificacao"] = s.js("window.__notif")
    s.fechar()
    s2 = Sessao(b, url, largura=900, altura=900)
    s2.definir(12, 34)
    s2.page.click("#principal")
    time.sleep(1.3)
    s2.page.screenshot(path=str(LOG / "tela_900px_rodando.png"))
    s2.page.click("#zerar")
    s2.fechar()
    fonte = Path(unquote(url[len("file:///"):])).read_text(encoding="utf-8")
    r["fonte_cita_Notification"] = "Notification" in fonte
    r["fonte_tem_http"] = "http://" in fonte or "https://" in fonte
    conferir(not r["pedidos_fora_de_file"], f"pedidos de rede: {r['pedidos_fora_de_file']}")
    conferir(r["pedidos_de_notificacao"] == 0 and not r["fonte_cita_Notification"], "pediu notificacao")
    conferir(not r["fonte_tem_http"], "o HTML aponta pra endereco de fora")
    return r, s.erros + s2.erros


TESTES = [t_contagem_3s, t_qualquer_tecla_para, t_pausar_continuar, t_zerar, t_tecla_espaco,
          t_negativos, t_horas_e_atalhos, t_relogio_real_pagina_congelada, t_persistencia_som,
          t_sons_embutidos, t_visual_e_isolamento]


def rodar_bateria(browser, html):
    url = html.resolve().as_uri()
    resultados = []
    for t in TESTES:
        ini = time.perf_counter()
        try:
            medidas, erros = t(browser, url)
            if erros:
                raise Falha("erros no console da pagina: " + "; ".join(erros))
            resultados.append({"teste": t.__name__[2:], "passou": True, "medidas": medidas})
        except Exception as e:  # noqa: BLE001  (o teste registra qualquer quebra)
            msg = str(e) if isinstance(e, Falha) else traceback.format_exc(limit=2)
            resultados.append({"teste": t.__name__[2:], "passou": False, "erro": msg.strip()[:600]})
        resultados[-1]["segundos"] = round(time.perf_counter() - ini, 2)
        print(("PASSOU " if resultados[-1]["passou"] else "FALHOU ") + resultados[-1]["teste"], flush=True)
    return resultados


def escrever_relatorio(normal, mutante, versao_chromium):
    linhas = ["# RESULTADO dos testes do cronômetro", "",
              f"Rodado em {datetime.datetime.now():%d/%m/%Y %H:%M} com Playwright + Chromium headless {versao_chromium}.",
              "Gerado por `testes/testar.py`; os números abaixo saem direto da medição (detalhe em `testes/log/resultado.json`).",
              "", "## Bateria normal", "", "|Teste|Resultado|Medidas|", "|-|-|-|"]
    for r in normal:
        med = json.dumps(r.get("medidas", r.get("erro")), ensure_ascii=False).replace("|", "/")
        linhas.append(f"|{r['teste']}|{'passou' if r['passou'] else 'FALHOU'}|{med}|")
    if mutante is not None:
        reprovados = [r["teste"] for r in mutante if not r["passou"]]
        linhas += ["", "## Mutação", "",
                   f"Cópia `testes/log/mutante.html` com `{TRECHO_FIM}` trocado por `{TRECHO_MUTANTE}` (o tempo nunca acaba).",
                   "", f"Testes que reprovaram no mutante: {len(reprovados)} de {len(mutante)} > {', '.join(reprovados) or 'NENHUM'}",
                   "", "|Teste no mutante|Resultado|Erro|", "|-|-|-|"]
        for r in mutante:
            linhas.append(f"|{r['teste']}|{'passou' if r['passou'] else 'reprovou'}|{(r.get('erro') or '').splitlines()[0][:160] if r.get('erro') else ''}|")
    (PASTA_TESTES / "RESULTADO.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", type=Path, default=RAIZ / "cronometro.html")
    ap.add_argument("--mutacao", action="store_true")
    ap.add_argument("--sem-relatorio", action="store_true")
    a = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch()
        versao = browser.version
        normal = rodar_bateria(browser, a.html)
        mutante = None
        if a.mutacao:
            fonte = a.html.read_text(encoding="utf-8")
            if fonte.count(TRECHO_FIM) != 1:
                sys.exit(f"trecho da mutacao achado {fonte.count(TRECHO_FIM)} vezes, esperado 1")
            mut = LOG / "mutante.html"
            mut.write_text(fonte.replace(TRECHO_FIM, TRECHO_MUTANTE), encoding="utf-8")
            print("--- mutante ---", flush=True)
            mutante = rodar_bateria(browser, mut)
        browser.close()

    (LOG / "resultado.json").write_text(json.dumps({"chromium": versao, "normal": normal, "mutante": mutante},
                                                   ensure_ascii=False, indent=2), encoding="utf-8")
    if not a.sem_relatorio:
        escrever_relatorio(normal, mutante, versao)
    ok = all(r["passou"] for r in normal)
    if mutante is not None:
        mut_reprovou = any(not r["passou"] for r in mutante)
        print(f"mutante reprovou: {mut_reprovou}")
        ok = ok and mut_reprovou
    print("TUDO CERTO" if ok else "HA FALHA")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
