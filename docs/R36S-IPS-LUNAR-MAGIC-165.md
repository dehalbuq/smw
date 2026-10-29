# Tradução PT-BR IPS e Lunar Magic 1.65: incompatibilidade confirmada

O IPS `Super Mario World (PT-BR).ips` enviado pelo testador inclui
literalmente `Lunar Magic Version 1.65` no registro que escreve o
marcador SNES `$0F:F0A0` (PC `0x7F0A0` com ROM sem header, offset IPS
`0x7F2A0` com header 512B). Isso explica o erro ao escolher o modo
"ROM modificada".

O `assets/compile_resources.py` da base exige exatamente
`Lunar Magic Version 3.33` e `get_byte(0x6F540)==0xc9` (layout
Map16), além de verificações posteriores de ExAnimation. O `-f`
de `restool.py` apenas desativa a verificação de SHA1; **não** torna
compatível o layout de ROM do LM 1.65.

## Recuperação sem corromper assets

1. Manter backup da ROM/IPS original; não modificar `smw_assets.dat`
   em produção.
2. Usar **Lunar Magic 3.33** numa cópia da ROM modificada (não 3.71,
   versão corrente do editor); a conversão pode falhar.
3. Seguir exatamente a orientação do compilador: modificar/salvar
   uma fase, a tabela Map16 e o ExAnimation. Guardar o original.
4. Testar a cópia convertida num emulador SNES antes de extrair.
5. Extrair com `python3 assets/restool.py -r ROM-CONVERTIDA.smc -f --no-include-rom`.
6. Inspecionar o resultado em ambiente isolado e não assumir que
   modificações ASM de hack funcionam no motor C reimplementado.

O extrator Windows GUI v2 disponível no chat detecta previamente
a assinatura do LM e recusa publicar assets de ROM incompatível,
gerando `saida/RELATORIO-COMPATIBILIDADE-ROM.txt`.
Ele não converte ROMs antigas automaticamente.

Referência editor: https://fusoya.eludevisibility.org/lm/program.html
