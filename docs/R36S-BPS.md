# R36S: traducao e sprites por patches BPS

O port aceita dados extraidos de uma ROM modificada, mas nao emula todas as
modificacoes ASM da ROM. Suporte a BPS **na preparacao dos recursos**, nao
simplesmente colocando o .bps na pasta do R36S.

## Como preparar uma ROM original sua com patch BPS

No computador com Python 3, dentro do checkout deste repositorio:

    python3 tools/preparar_bps.py smw-original.sfc traducao.bps --rom-out smw-ptbr.sfc --assets-out smw_assets_ptbr.dat

O script:
1. verifica estrutura e CRC32 da origem e do arquivo BPS;
2. aplica as operacoes BPS1 e confere o CRC32 do resultado;
3. roda assets/restool.py --rom smw-ptbr.sfc --no-hash-check em pasta temporaria;
4. salva smw_assets_ptbr.dat sem sobrescrever o smw_assets.dat existente.

No R36S, faca backup do arquivo anterior e copie o novo como:

    /roms/ports/smw-r36s/smw_assets.dat

O executavel smw ARM64 nao precisa ser recompilado se a mudanca afetar
apenas tabelas, graficos e recursos que o extrator/port ja suportam.

Se desejar apenas testar a aplicacao BPS, sem extracao dos assets:

    python3 tools/preparar_bps.py smw-original.sfc traducao.bps --no-assets

**Observacoes e limites:**
- A ROM base deve ser a versao exata exigida pelo BPS (CRC32), com ou sem
  cabecalho de 512 bytes conforme o patch. O script nao remove cabecalho
  automaticamente, pois isso invalidaria a verificacao BPS.
- Traducao que modifica fontes, graficos/tiles e dados ja lidos do ROM
  **pode** funcionar. Texto que depende de novos hooks ou codigo ASM
  precisara de adaptacao no C do port.
- Melhorias de sprites via CHR/GFX/ExGFX e mapas ja suportados pelo extrator
  **podem** funcionar; formatos, rotinas ou pointers novos exigem analise.
- O port reimplementa a logica em C: BPS que adiciona codigo para o
  processador 65c816 do SNES nao muda automaticamente o executavel ARM64.
- O extrator pode falhar ou gerar assets incompletos em hacks incompativeis.
  Por isso teste fases e menus depois de cada patch.
- Varios patches BPS feitos para a ROM limpa nao necessariamente podem ser
  aplicados em sequencia. Cada patch verifica o CRC da sua fonte; se houver
  conflito, sera preciso combinar as alteracoes na ROM antes de gerar assets.
- O script nao baixa nem distribui a ROM original, ROM modificada, patch de
  terceiros ou dados proprietarios.
- Patches com alteracoes grandes podem produzir divergencias na
  verificacao com o emulador de referencia. Um modo alternativo e gerar
  sem ROM inclusa com --without-rom-compare, mas isso precisa de teste
  em hardware e pode limitar alguns recursos.

Para avaliarmos **a traducao e o pacote de sprites especificos**, forneca
os arquivos .bps ou seus links e, se houver, as instrucoes do autor.
Vamos verificar CRC, revisao de ROM, alteracoes de tiles/texto e ASM
antes de considerar a compatibilidade confirmada.
