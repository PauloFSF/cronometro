# Cronômetro

Cronômetro regressivo num arquivo só, `cronometro.html`. Não precisa de internet nem de instalar nada.

## Como abrir

Dois cliques em `cronometro.html`. Abre no navegador padrão.

## Como usar

* Clique nos números do centro pra digitar os minutos e os segundos (as setas pra cima e pra baixo também mudam o tempo), ou use os atalhos de 5, 10, 15 e 25 min.
* **Iniciar**, **Pausar**, **Continuar** e **Zerar**. No teclado: `Espaço` inicia ou pausa, `Esc` zera.
* Quando chega a zero, o som toca sem parar e o anel pulsa até você clicar em **Parar som** ou apertar qualquer tecla.
* A conta é feita pelo relógio. Se a aba ficar em segundo plano, o tempo não atrasa.

## Como trocar o som

* Os três sons que vêm prontos ficam na lista: beep clássico, sino suave e alarme digital.
* **Trocar som** abre o seletor de arquivo. Aceita MP3, WAV ou OGG. O arquivo fica guardado no navegador e continua lá quando você fecha e abre de novo.
* **Testar** toca o som escolhido. Clicando de novo, ele para.
* **Voltar ao padrão** apaga o arquivo guardado e volta pro beep clássico.
* O volume também fica guardado.

O som fica guardado no navegador em que você escolheu o arquivo. Abrindo em outro navegador, você precisa escolher o arquivo de novo.

## Como rodar os testes

Precisa do `uv`. Da pasta do repositório:

```
uv run --no-project --with playwright==1.65.1 python testes/testar.py --mutacao
```

Na primeira vez, se o Chromium do Playwright não estiver instalado:

```
uv run --no-project --with playwright==1.65.1 playwright install chromium-headless-shell
```

O resultado vai pra `testes/RESULTADO.md`. O detalhe e as capturas de tela ficam em `testes/log/`, que fica fora do git.
