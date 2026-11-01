# Tradução PT-BR ampliada — SMW (R36S / Android ARMv7)

O usuário fornece seu próprio `smw_assets.dat` original corrigido de **880.156 bytes**.
O arquivo modificado **não** está versionado neste repositório por conter
dados extraídos da ROM comercial. Uma versão modificada para uso pessoal
foi entregue em anexo na conversa.

A tradução modificou **5 recursos** do pacote, sempre mantendo o mesmo
número de bytes de cada recurso e todos os offsets:

| Recurso | Alteração |
|---|---|
| `kDisplayMessage_DATA_05A5D9` | 22 mensagens distintas (25 entradas incluindo reutilizações), incluindo o título `PALACIO BOTAO` |
| `kUpdateLevelName_LevelNameStrings` | 46 fragmentos de nomes do mapa |
| `kFileSelectText_EraseFile` | Termos `EMPTY`, `ERASE`, `END`, `DATA` |
| `kGameMode1B_EndingCinema_Tilemaps` | 14 títulos de funções da equipe nos créditos (sem mudar nomes das pessoas) |
| `kLoadStripeImagePtrs` | 32 nomes/descrições de inimigos dos créditos finais |

Apenas tiles de texto reconhecidos foram alterados, sem modificar atributos
de tiles, ponteiros, terminadores das mensagens ou grupos compactados.

No **código C** desta branch, `GameMode00_LoadNintendoPresents()`
desenha **sprites invisíveis** no lugar da vinheta inicial do
fabricante, sem pular uma etapa, modificar sprites do jogo,
som/fades ou corromper o relógio de inicialização.
As sequências fixas `COURSE CLEAR!` e `BONUS!` passam a
`FASE VENCIDA!` e `EXTRA!`, com o mesmo número de tiles.

Esta edição **não altera avisos de direitos autorais, licenças,
nomes de pessoas** nos créditos nem o metadado da ROM. Textos que
fazem parte de imagens/tilemaps ainda não completamente identificados
podem permanecer em inglês, incluindo possível aviso em tela de
título. Não declarar localização 100% completa nem remoção global
de referências visuais ao fabricante.

A versão do jogo só tem esses textos fixos em português usando o
**novo executável compilado**. Apenas instalar o DAT não substitui
as mensagens definidas diretamente no C nem oculta a vinheta.

Validação binária: 880.156 bytes, índice e SHA de nomes preservados,
173 de 178 recursos intactos, quatro tabelas de entrada secundária
do Vanilla Dome 1 preservadas, sem realocação de dados.

Builds de CI:
- [R36S ARM64 release](https://github.com/dehalbuq/smw/actions/runs/41341558096)
- [Android ARMv7 APK](https://github.com/dehalbuq/smw/actions/runs/41341562455)

Por causa de diferenças de gráfico e modelo de exibição, é necessário
testar menus, créditos e caixas de diálogo no dispositivo físico.
