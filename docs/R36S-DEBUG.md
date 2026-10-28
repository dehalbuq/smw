# Super Mario World: porta R36S / DarkOSRE / ARM64

## Estado

Este fork preserva o projeto original do snesrev/smw e acrescenta o trabalho
especifico para o R36S (Rockchip RK3326, quatro nucleos Cortex-A35).
Versao inicial de **diagnostico**: nao corrige ainda o crash na troca de fases.
Nao inclui ROM, smw_assets.dat ou executavel.

Os fontes extras ficam em overlay/src, ferramentas em tools e scripts em port.
Durante o GitHub Actions, tools/apply_overlay.py instrumenta src/main.c apenas
no ambiente temporario do build. O codigo original do fork nao e sobrescrito.

## Compilacao ARM64 sem PC

1. Abra a aba **Actions** do fork dehalbuq/smw.
2. Se necessario, habilite os workflows pela interface do GitHub.
3. Abra **SMW R36S ARM64 Debug** e escolha **Run workflow** (branch main).
4. Quando finalizar, baixe o artefato **smw-r36s-arm64-debug**.
5. O ELF deve ser AArch64 e compilado com -O2 -mcpu=cortex-a35.
   O Debian bookworm fornece glibc 2.36; a compatibilidade real com
   DarkOSRE depende das bibliotecas presentes no dispositivo. Se surgir
   GLIBC_2.36 not found, sera preciso refazer a build com sysroot antigo.

O workflow nao precisa do arquivo de recursos para compilar.

## Instalacao no console

Estrutura esperada no cartao:

    /roms/ports/
        SMW-R36S-Debug.sh
        smw-r36s/
            smw
            smw.ini
            smw_assets.dat   <-- COPIE O SEU ARQUIVO AQUI
            logs/
            saves/
            playthrough/

Em sistemas com segundo cartao, a pasta pode estar em /roms2/ports.
O launcher cria logs, saves e playthrough automaticamente.
O arquivo smw_assets.dat deve permanecer **fora do repositorio publico**.

Coloque o launcher na pasta ports e o binario ARM64 em smw-r36s/smw.
Se necessario, aplique chmod +x nos arquivos executaveis.
Inicialize via menu Ports.

### Menu de saida (build de 28/10/2026)

No R36S, segure **SELECT por aproximadamente um segundo** para abrir o menu
**SAIR DO JOGO?**. Com o menu aberto:

- START: confirma SAIR DO JOGO e encerra normalmente, gravando o log.
- SELECT: cancela e volta ao jogo.
- A: confirma a saida.
- B: cancela.
- Teclado USB: ESC abre/fecha o menu e ENTER confirma.

**Saida de emergencia:** segure SELECT + START juntos durante pelo menos
3 segundos. O jogo encerra mesmo que a janela do menu nao desenhe.

O menu pausa a simulacao e o som enquanto estiver visivel.
Os registros esperados sao [EXIT_MENU], [EXIT_REQUEST], [SHUTDOWN]
no log de diagnostico e game_exit_status=0 no log do launcher.

Observacao: a placa GO-Super Gamepad detectada no DarkOSRE tem raw joystick
SELECT=b12 e START=b13, apesar de esses botoes faltarem no mapeamento
SDL_GameController. Outros modelos podem definir
SMW_R36S_SELECT_BUTTON e SMW_R36S_START_BUTTON no launcher.


## START / SELECT no R36S

Esta build possui fallback para botões **brutos SDL_JOYBUTTON**:
SELECT = indice 12 e START = indice 13 (padrao publicado para R36S).
Ela tambem continua aceitando os eventos SDL GameController convencionais.
O mecanismo pode variar de acordo com a revisao da placa e o firmware.

Pressione SELECT e START separadamente no inicio do jogo e depois
juntos por 2 segundos. Os logs agora incluem eventos `[RAW_JOY]`,
`[MENU_BUTTON]` e `[CONTROLLER_MAPPING]`, uteis para confirmar
a numeracao real. O teste em hardware e necessario para validar o ajuste.

Se seu aparelho usa indices diferentes, coloque antes da linha
`if [ "${SMW_EXTERNAL_ROM:-0}"...` do script de inicializacao:

    export SMW_R36S_SELECT_BUTTON=12
    export SMW_R36S_START_BUTTON=13

Altere 12/13 conforme os indices reportados no log. Se nao aparecer
nenhum evento `[RAW_JOY]`, envie os registros para diagnosticar
eventos SDL ou teclado remapeado.

Para patches de traducao/graphics BPS, leia docs/R36S-BPS.md.

## Investigacao de crashes

Os logs sao armazenados em:

- smw-r36s/logs/r36s-diagnostic.log: quadro, modo, fase (0x13BF),
  coordenadas, entradas, mudancas de modo e fatal signals com PC/SP em AArch64.
- smw-r36s/logs/run-AAAAMMDD-HHMMSS.log: informacoes do sistema,
  arquitetura ELF, dependencias e codigo de saida do processo.

Pode haver snapshots de divergencia em smw-r36s/saves e playthrough.
Lembrete: esses snapshots podem conter dados extraidos da ROM.

No PC, execute:

    python3 tools/analisar_log.py r36s-diagnostic.log run-AAAAMMDD-HHMMSS.log

Para traduzir um PC de erro em funcao/linha, use os simbolos
debug-symbols/smw.debug disponibilizados no artefato do workflow:

    aarch64-linux-gnu-addr2line -f -C -e smw.debug 0xENDERECO

Os enderecos sao estaveis entre execucoes porque o build usa -no-pie.
Nao execute o argumento upstream --debug durante os testes iniciais:
ele tem uma logica de repeticao de frame ao ocorrer divergencia.

**Testes**: primeiro sem modificar os parametros do pacote.
Se reproduzir o problema, experimente NewRenderer=0 no smw.ini.
Depois teste OutputMethod=SDL em vez de SDL-Software, alterando somente
uma opcao a cada execucao.

## Comparacao com o emulador de referencia

O restool original normalmente inclui a ROM nos recursos extraidos.
Se smw_assets.dat foi gerado com --no-include-rom, a comparacao e desligada,
a menos que a ROM seja fornecida separadamente.
Nenhuma ROM deve ser publicada neste fork.

## Limites e roadmap

- Versao de debug ainda nao testada no hardware real.
- Launcher destinado a instalacao manual, nao e pacote oficial do PortMaster.
- Sem garantia de glibc, video ou audio no DarkOSRE sem um teste local.
- Proximos passos: capturar log do crash, corrigir a causa, medir desempenho,
  e implementar uma camada opcional de traducao PT-BR sem alterar assets base.
