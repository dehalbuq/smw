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
- **AudioSamples=1024** a 32000Hz (~32ms nominal). Nos logs do R36S,
  512 amostras causaram ALSA underruns; se o firmware for estavel,
  512 pode ser testado em busca de menor latencia, sabendo do risco de estalos.
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
AudioSamples = 1024
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
1. Inspecionar `python3 tools/prepare_ips_smw.py --ips "Super Mario World (PT-BR).ips" --inspect`.
2. Aplicar a copia `python3 tools/prepare_ips_smw.py --ips "Super Mario World (PT-BR).ips" --rom smw.sfc --output smw-ptbr.smc --ips-headered`.
3. Executar `python3 assets/restool.py -r smw-ptbr.smc -f --no-include-rom`.
4. Testar o novo `smw_assets.dat` separado dos assets/saves originais.
5. Verificar titulo, caixas de mensagem, nomes, sprites/tiles e fases.
6. Se falhar o extrator, o IPS depende de layout/ASM que exige
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

## Investigação de sala bônus inacessível (30/10/2026)

Log enviado: `run-20250904-003127.log`. Próximo ao quadro **25351**, após
uma transição `0f → 10 → 11 → 12 → 13 → 14`, o Mario reapareceu em
`(16,0)` e depois permaneceu na sala; quadros 25440–26880 mostram saltos
com Y até próximo de `0xffdd` (posição negativa assinada).
O campo `level=3e` era o número da fase do overworld, que não muda
necessariamente ao carregar salas bônus/portas/canos.

Não há prova suficiente para alterar coordenadas de blocos ou colisão.
Foi adicionada instrumentação de **somente leitura**:
- `[LEVEL_ASSET]`: índice real do nível carregado, incluindo sublevel
- `[SUBLEVEL]`: número de subníveis entrados, bônus, câmera, posição
- `[BONUS_SPRITES]`: coordenadas dos objetos sprite `0x82` (roleta de 1-UP)

Reproduzir com a mesma versão/mesmo `smw_assets.dat`, entrar novamente
na sala e recolher os novos logs, se possível com foto do defeito.
As métricas vistas foram ~58.3–58.6 FPS com VSync=1 e múltiplos
`ALSA underrun`, razão para priorizar estabilidade do áudio.

## Recuperação experimental do cano — Vanilla Dome 1 (30/10/2026)

A nova execução com `[LEVEL_ASSET]` identificou:
`11A` → `1EF` (correto) → `100` (indevido em cano normal).
Na sala `100`, os sprites `0x82` da roleta aparecem no mundo com
Y de 240 a 320, mas Mario fica no Y 160 e a câmera no Y zero.
A tela não está simplesmente fora de escala: é a sala incorreta.

**Solução temporária e reversível apenas nesta branch:**
A nova rotina `r36s_vd1_pipe.c` primeiro tenta recuperar a entrada
secundaria correta a partir da **tabela de entradas dos próprios
assets da ROM**, procurando uma unica entrada para `11A`, acima
do oitavo screen (continuação da primeira area da fase). Quando ha
uma correspondencia unica, deixa o carregador original definir
a posição inicial do Mario e da câmera, sem inventar coordenadas.
Novo log: `[VD1_SECONDARY_FIX]`.

Se a tabela não contiver uma entrada inequívoca, o fallback
experimental memoriza a posição e câmera de Mario na transicao
`11A → 1EF` e retorna para `11A` perto do cano anterior
(64 pixels à direita, 16 acima), com log
`[VD1_SECONDARY_SCAN]` seguido de `[VD1_PIPE_RECOVERY]`.
Esse fallback não é o destino oficial verificado e pode reaparecer
num local inapropriado. Não modifica a geometria nem a colisão
da sala bônus legitima.

Ligue/desligue com a variável de ambiente no script launcher:
`SMW_R36S_VD1_PIPE_FIX=1` (ativado por padrão) ou
`SMW_R36S_VD1_PIPE_FIX=0` (comportamento anterior, para comparação).
Novos logs `[VD1_INVALID_EXIT]` registram destino e tabela de
saídas dos screens anterior, atual e posterior, e
`[VD1_PIPE_RECOVERY]` documenta as posições recuperadas.

**Para corrigir a rota definitivamente, precisamos extrair o destino
real da entrada de cano a partir do `smw_assets.dat` de teste.**
Os símbolos `.debug` não contêm os recursos da ROM, portanto
não permitem identificar as saídas da fase gravadas no pacote.
Não mesclar sem validar o retorno a `11A` em hardware.
