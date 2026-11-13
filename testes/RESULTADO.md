# RESULTADO dos testes do cronômetro

Rodado em 13/11/2026 13:06 com Playwright + Chromium headless 158.0.8127.18.
Gerado por `testes/testar.py`; os números abaixo saem direto da medição (detalhe em `testes/log/resultado.json`).

## Bateria normal

|Teste|Resultado|Medidas|
|-|-|-|
|contagem_3s|passou|{"duracao_relogio_do_teste_s": 3.075, "duracao_dentro_da_pagina_ms": 3072.6, "titulo_rodando": "00:03 · Cronômetro", "titulo_fim": "Tempo esgotado · Cronômetro", "som_no_fim": {"tocando": true, "loop": true, "contexto": "running", "escolhido": "beep"}, "som_1_6s_depois": true, "som_apos_parar": false}|
|qualquer_tecla_para|passou|{"tocando_antes": true, "tocando_depois_da_tecla_a": false}|
|pausar_continuar|passou|{"icone_rodando_play_pausa_rotulo": [false, true, "Pausar"], "icone_pausado": [true, false, "Continuar"], "display_pausado": "00:09", "restante_pausado_ms": 8754.6, "restante_1_5s_depois_ms": 8754.6, "andou_1_1s_apos_continuar_ms": 1104.1}|
|zerar|passou|{"apos_botao_zerar": ["01", "30", "parado"], "apos_esc": ["01", "30", "parado"]}|
|tecla_espaco|passou|{"sequencia": ["rodando", "pausado", "rodando"], "espaco_com_foco_no_botao": "rodando"}|
|negativos|passou|{"iniciar_desabilitado_em_00_00": true, "estado_apos_espaco_em_00_00": "parado", "digitar_ab": "", "digitar_-5": "5", "colar_-3": "3", "0_min_75_s": "01:15", "2_min_99_s": "03:39"}|
|horas_e_atalhos|passou|{"atalho_25": "25:00", "display_90_min": "1:30:00", "atalho_desabilitado_rodando": true}|
|relogio_real_pagina_congelada|passou|{"voltou_em_s": 2.536, "restante_ao_voltar_ms": 1493.2, "esperado_ms": 1464.3, "fim_em_s": 4.04}|
|persistencia_som|passou|{"wav_bytes": 22094, "arquivo_invalido_erro": "Esse arquivo não é um áudio que eu consiga tocar (use MP3, WAV ou OGG).", "arquivo_invalido_escolhido": "beep", "nome_apos_recarregar": "teste_440hz.wav", "select_apos_recarregar": "personalizado", "blob_apos_recarregar": {"nome": "teste_440hz.wav", "bytes": 22094, "tipo": "audio/wav", "eh_blob": true}, "testar_tocando_loop": [true, false], "fim_com_meu_som_1_2s_depois": {"tocando": true, "loop": true, "contexto": "running", "escolhido": "personalizado"}, "volume_apos_recarregar": "30", "apos_padrao_select": "beep", "apos_padrao_nome_visivel": false, "apos_padrao_blob": null}|
|sons_embutidos|passou|{"beep": {"duracao_s": 1.4, "pico": 0.55, "rms": 0.1961, "testar_tocou": true}, "sino": {"duracao_s": 2.8, "pico": 0.838, "rms": 0.0902, "testar_tocou": true}, "alarme": {"duracao_s": 1.1, "pico": 0.192, "rms": 0.064, "testar_tocou": true}}|
|visual_e_isolamento|passou|{"largura_conteudo_em_400px": 400, "pedidos_fora_de_file": [], "pedidos_de_notificacao": 0, "fonte_cita_Notification": false, "fonte_tem_http": false}|

## Mutação

Cópia `testes/log/mutante.html` com `restante(agora) <= 0` trocado por `restante(agora) < 0` (o tempo nunca acaba).

Testes que reprovaram no mutante: 5 de 11 > contagem_3s, qualquer_tecla_para, relogio_real_pagina_congelada, persistencia_som, visual_e_isolamento

|Teste no mutante|Resultado|Erro|
|-|-|-|
|contagem_3s|reprovou|Traceback (most recent call last):|
|qualquer_tecla_para|reprovou|Traceback (most recent call last):|
|pausar_continuar|passou||
|zerar|passou||
|tecla_espaco|passou||
|negativos|passou||
|horas_e_atalhos|passou||
|relogio_real_pagina_congelada|reprovou|Traceback (most recent call last):|
|persistencia_som|reprovou|Traceback (most recent call last):|
|sons_embutidos|passou||
|visual_e_isolamento|reprovou|Traceback (most recent call last):|
