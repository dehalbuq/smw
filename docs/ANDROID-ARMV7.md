# SMW Android ARMv7 / 32-bit — instalação experimental

Esta ramificação cria um APK **exclusivamente para `armeabi-v7a`**,
usando o **motor nativo atualizado de dehalbuq/smw**, a camada de aplicação
Android SDL2 de [freyta/smw-android](https://github.com/freyta/smw-android),
e o Android NDK r25c.

- APK separado: `com.dehalbuq.smw`
- ABI: `armeabi-v7a` (32 bits), **sem** `arm64-v8a`
- Android mínimo: **6.0 (API 23)** neste primeiro build
- SDL2: entrada de gamepads Bluetooth/USB reconhecidos pelo Android,
  mapeamento padrão SNES, controles na tela da camada Android
- Gráficos: renderizador SDL acelerado (OpenGL ES no Android)
- O arquivo `smw_assets.dat` **não é incluído no APK**
- As tabelas de entradas secundárias do SMW vanilla precisam estar
  presentes no arquivo de assets (use o arquivo **corrigido** do R36S).

## Build automático

[GitHub Actions → Android ARMv7 APK](https://github.com/dehalbuq/smw/actions/workflows/build-android-armv7.yml).

O fluxo baixa a camada de Android `freyta/smw-android`, coloca os módulos
nativos `smw_*.c` e dependências do seu fork, preserva `main.c`,
`util.c` e `config.c` específicos do Android, força a ABI de 32
bits e executa `assembleDebug`. A assinatura de depuração serve
apenas a testes locais; não serve para publicação na Play Store.

## Instalação e arquivos necessários

1. Instalar o APK em aparelho ARMv7 compatível, permitir instalação de
   fontes confiáveis quando solicitado pelo Android.
2. Conectar/parear o controle Bluetooth **antes** de abrir o jogo.
3. Colocar `smw_assets.dat` legítimo extraído da **sua ROM original**
   e com as tabelas secundárias corrigidas em
   `Android/data/com.dehalbuq.smw/files/smw_assets.dat`
   no armazenamento externo do dispositivo.
4. Iniciar o aplicativo. `smw.ini` é copiado para o diretório do app
   pela camada Java do port original. Ajustar `[GamepadMap]` caso
   o controle não tenha mapeamento SDL conhecido.

**Observações:**
- Um APK nativo ARMv7 não roda em sistemas exclusivamente 64 bits que
  não oferecem o ABI secundário de 32 bits.
- Suporte a Bluetooth depende do mapeamento de controles do próprio Android
  e da versão do SDL empacotada. A compilação não garante funcionamento
  de todo controle Bluetooth.
- A resolução/áudio/taxa de quadros dependem do aparelho. O código não
  promete 60 FPS em Android antigo.
- O fundo `background.png` e o launcher de PortMaster do R36S não são
  componentes desta primeira versão: o Android usa o renderizador SDL
  e sua configuração própria.
