# SMW R36S: desempenho 4:3 e pixel-perfect (experimental)

Branch independente de `main`: `feature/r36s-performance-43-pixelperfect`.

## O que foi alterado

- **16:9 retirado por completo:** nao ha compositor, Map16 widescreen, nem
  alteracoes no tamanho do PPU. Frame de jogo nativo: **256x224**.
- **PixelPerfect=1:** em tela fisica 640x480, scale inteiro **2x**:
  frame **512x448**, margens pretas **64px esquerda/direita** e
  **16px em cima/baixo**. `GL_NEAREST` e SDL nearest; sem filtros.
- **PixelPerfect=0:** correcao de aspecto 4:3 para ocupar mais tela,
  mas escala fracionaria e colunas desiguais. Nao e pixel perfect.
- **OutputMethod=OpenGLES2:** backend GPU OpenGL ES 2.0 com SDL/GLSL ES,
  compilado separadamente. `smw` e executavel SDL independente do GLES.
- **VSync=1:** evita tearing quando o driver respeita o swap interval.
  `VSync=0` pode reduzir latencia, mas corre risco de tearing.
- **Frame pacing** com contador de alta resolucao (60Hz) no lugar do
  loop original 17/17/16ms. Log `[PERF]` mostra FPS a cada 600 quadros.
- **Native-only:** desabilitada a execucao paralela do emulador de
  comparacao (modo `RM_MINE`) SOMENTE nesta branch/build; o motor C
  original segue sendo executado. Ganha CPU, mas perde verificacao
  de divergencias; mantenha a build debug antiga para reportar bugs.
- **Cortex-A35** `-O3 -flto -fno-strict-aliasing -fwrapv`, secao GC.
  Sem `-ffast-math`, evitando mudancas arriscadas de semantica.
- **AudioSamples=512** a 32000Hz (~16ms de buffer SDL nominal).
  AudioSamples=1024 pode ser mais confiavel em firmwares que estalam.
- SELECT/START continua preservado, assim como saves/snapshots.

## Configuracao

```ini
[General]
DisableFrameDelay = 0
SavePlaythrough = 0

[Graphics]
WindowSize = 640x480
Fullscreen = 1
IgnoreAspectRatio = 1
PixelPerfect = 1
VSync = 1
OutputMethod = OpenGLES2
LinearFiltering = 0

[Sound]
AudioFreq = 32000
AudioSamples = 512
```

Use `OutputMethod = SDL-Software` para comparar CPU e GPU; o launcher
tambem tenta fallback caso `smw-gles2`/bibliotecas estejam ausentes.
Preferencias em `smw.ini` nao sao reescritas automaticamente.

**4:3 do console vs pixels quadrados:** SNES desenha 256x224 (8:7),
nao 4:3 em coordenadas quadradas. PixelPerfect=1 preserva quadrados
exatos; por isso deixa barras maiores dos lados da tela 4:3. Emular
a correcao de aspecto CRT 4:3 e simultaneously manter escala inteira
em ambos os eixos nao e possivel em 640x480 com esses 256x224 pixels.

## Patch IPS de traducao PT-BR: analise do arquivo enviado

Arquivo `Super Mario World (PT-BR).ips` analisado sem
incluir o arquivo binario no repositorio.
IPS valido, 1.585 registros, 1.033.620 bytes escritos; endereco final
`0x100200` (**1 MiB + 512 bytes**) e dados que correspondem a ROM
original *com* cabecalho copier de 512 bytes. Portanto NUNCA executar o
patch diretamente sobre `smw_assets.dat` nem sobre `smw`.

O snesrev/smw usa codigo fonte C e `smw_assets.dat` **extraido de ROM**.
Patches IPS/BPS modificam ROM 65816; mudancas de texto/graficos podem
ser extraidas, mas ASM, controle de jogo, engines ou hooks proprios
nao serao executados pelo port C. Para sprite-swap futuro, sprites de
ROM podem ser compatíveis quando extraidos, mas alterações ASM não são.

Fluxo de teste **local**, com ROM de SMW US legalmente adquirida:
1. Aplicar o IPS a copia da ROM compativel, respeitando cabecalho 512.
2. Executar `python3 assets/restool.py -r ROM_PATCHED.smc -f --no-include-rom`.
3. Testar o novo `smw_assets.dat` separado dos assets/saves originais.
4. Verificar titulo, caixas de mensagem, nomes, sprites/tiles e fases.
5. Se falhar o extrator, o IPS depende de layout/ASM que exige
   adaptacao no motor C ou um mapeamento de dados.

**Atencao:** o IPS nao informa hash nem revisao da ROM original.
Sem a ROM base, nao se pode provar compativel nem afirmar que traduz
todas as mensagens. O patch tambem reescreve trechos extensos da ROM,
portanto pode nao ser simples substituicao de texto.

## Testes pendentes no R36S fisico

Compilacao CI confirma arquitetura e linking, **nao** prova FPS nem
input latency. Comparar dois perfis `VSync=1` vs `VSync=0`, observar
tearing, verificar `[PERF] avg_fps`, controle/saida SELECT, som e saves.
Testar ambos `OpenGLES2` e `SDL-Software`, sem trocar assets entre
versions de forma irreversivel.
