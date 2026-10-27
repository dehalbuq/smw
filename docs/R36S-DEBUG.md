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
Inicialize via menu Ports. Para sair, segure SELECT + START por dois segundos.

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
