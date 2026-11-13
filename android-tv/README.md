# Super Mario World Recomp — Android TV experimental (ARM64)

Android TV port of the SAME mstan/SuperMarioWorldRecomp engine used by our
verified R36S dArkOSRE build. This is **native Android NDK** (not the Linux
R36S ELF repackaged).

Features planned for private APK:
- Android TV/Google TV launcher (LEANBACK_LAUNCHER), also visible on phones;
- landscape and immersive fullscreen, screen ratio 16:9 with native adaptive
  widescreen render (not artificially stretched 4:3 video);
- USB/Bluetooth gamepad and TV remote through SDL2, **no touch overlay**;
- GLES2 and SDL2 native ARM64, persistent saves in internal app storage;
- a private ROM asset bundled only into the owner's PRIVATE CI artifact.

ROM note: ROM belongs exclusively in the user-owned PRIVATE repo
`dehalbuq/smw-rom-private` and the privately generated APK. Never publish
an APK containing copyrighted game ROMs publicly. The CI copies it into
the APK assets for PERSONAL testing. The code repo is ROM-free.

Android API min: 21 (Android 5.0); target TV ARM64 first. ARMv7 32-bit can be
added once the arm64 build runs on real Android and native ABI compatibility
is established.

The launch bridge copies the private ROM to the app-internal directory on first
run, enables adaptive 16:9 via SMW_RENDER_ASPECT=16:9, and invokes the original
SMW engine directly without a desktop file picker. Some SNES title/transition
scenes remain native 4:3 by engine design.

**STATUS:** work in progress; APK must compile AND be tested on a real Android
TV before claiming working graphics, gamepad, audio, and saves.
Check GitHub Actions private workflow:
https://github.com/dehalbuq/smw-rom-private/actions

Local diagnostics: Android `adb logcat -d -s SDL AndroidRuntime` and
`adb shell dumpsys package com.dehalbuq.smwrecomp`.


## Registro de validações em 13/11/2026

- O aparelho R36S com dArkOSRE já executou o SMW Recomp Linux ARM64 (projeto anterior).
- Android TV privado: workflow [#43510717353](https://github.com/dehalbuq/smw-rom-private/actions/runs/43510717353) concluiu com falha em `compileDebugJavaWithJavac`: JRE 21, mas `javac` ausente.
- A primeira tentativa de correção [#43512608877](https://github.com/dehalbuq/smw-rom-private/actions/runs/43512608877) não pôde instalar JDK com `sudo` porque o runner `smwrunner` não tem senha interativa.
- Corrigido no workflow privado: instalar JDK Temurin 21 completo em `$HOME/.local/smw-jdk21`, verificar SHA256 oficial, validar `bin/javac`, reutilizar cache sem acesso root.
- Em [#43512795821](https://github.com/dehalbuq/smw-rom-private/actions/runs/43512795821), tentativa 1, Java, SDK, clone, código SNES e preparação Android passaram. A ligação nativa falhou em `getifaddrs/freeifaddrs` na biblioteca `recomp-net`, não disponível no nível Android API 21.
- Correção no `android-tv/scripts/prepare-game.py`: evitar o `snesrecomp_enable_recomp_net(SuperMarioWorldSNESRecomp)` **somente no Android**. Objetivo: versão offline para Android TV, sem netplay e com Android 5.0 (API 21) como alvo mínimo. Linux/R36S não muda.
- A tentativa 2 do mesmo [#43512795821](https://github.com/dehalbuq/smw-rom-private/actions/runs/43512795821) foi disparada após esse patch. Verificar conclusão e artefatos antes de declarar APK jogável.
- Teste público [#43461833361](https://github.com/dehalbuq/smw/actions/runs/43461833361): 167/167 módulos nativos Android ARM64 compilados, sem ROM; em [#43462468148](https://github.com/dehalbuq/smw/actions/runs/43462468148) a configuração de fullscreen e armazenamento app-private também foi validada.

**Próximo passo:** conferir o log de `buildCMakeDebug[arm64-v8a]` na tentativa 2, corrigir possíveis erros remanescentes, obter `libmain.so` completo, publicar APK **exclusivamente** no artefato privado e testar na TV com gamepad USB/Bluetooth, áudio, widescreen e saves. A ROM nunca entra no repositório público.
