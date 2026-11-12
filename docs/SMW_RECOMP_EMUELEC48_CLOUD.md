# SMW Recomp — build ARM64 SDL2/GLES2 100% no GitHub Actions

Este laboratório fica **isolado** do motor snesrev e dos releases do R36S já existentes neste repositório. O workflow clona *mstan/SuperMarioWorldRecomp* em um diretório temporário e aplica o kit somente ali.

## Usar sem Kali, WSL ou compilação local

1. Abra **Code > Add file > Upload files** em `dehalbuq/smw` pelo navegador.
2. Envie o arquivo `SMWRecomp_EmuELEC48_GLES2_Kit.zip` disponível na conversa. Ele pode ficar **na raiz deste repositório** (caminho mais simples). Este ZIP não contém ROM e pode ficar público.
3. Abra **Actions > SMW Recomp EmuELEC 4.8 ARM64 - Cloud > Run workflow**. Primeiro escolha `audit`. Verifique se o log detecta o patch GLES2, mods e widescreen.
4. Para compilar todo o jogo, crie **outro repositório privado** no GitHub, por exemplo `dehalbuq/smw-rom-private`. Pelo navegador, carregue sua cópia legal e verificada de *Super Mario World (USA)* como **`smw.sfc` na raiz** desse repositório privado. **Nunca envie a ROM para este repositório público!**
5. Crie no GitHub um Fine-grained Personal Access Token com acesso de leitura de conteúdo **somente** ao repositório privado com sua ROM.
6. Neste repositório público (`dehalbuq/smw`), abra **Settings > Secrets and variables > Actions > New repository secret** e crie:
   - `SMW_PRIVATE_ROM_REPO`: nome do seu repositório privado, por exemplo `dehalbuq/smw-rom-private`.
   - `SMW_PRIVATE_ROM_TOKEN`: token de leitura desse repositório privado.
7. No workflow, clique em **Run workflow**, escolha modo `full`. Ele baixará a ROM durante a execução, verificará seu SHA-256, regenerará `src/gen`, aplicará o kit, compilará ARM64 e **não incluirá a ROM no artifact**.
8. Na página da execução, baixe o artifact `SMWRecomp-ARM64-SDL2-GLES2-ABI-UNVERIFIED`. Se falhar, mande o link da execução e o artifact de diagnóstico.

## O que permanece no código

- Widescreen adaptativo, HUD reposicionado e spawning adaptativo implementados em `src/smw_renderer.c` e nos mods;
- coop nativo experimental e demais melhorias de gameplay;
- suporte a controle SDL2 e áudio;
- infraestrutura de mods e dados estáticos do launcher.

## Qualificação

**Não é um release certificado para EmuELEC 4.8.** O runner `ubuntu-24.04-arm` produz um ELF AArch64 com dependências do Ubuntu; bibliotecas de sistema, carregador dinâmico, libc e drivers EGL/GLES2 do EmuELEC podem não ser compatíveis. O próximo estágio é cruzar com o SDK/sysroot real do EmuELEC 4.8 para a variante de hardware desejada e validar o executável no dispositivo. O artifact contém `ABI-REPORT.txt` com as dependências.

Os shaders GLSL 330 customizados de desktop não são portados para GLES2; a saída widescreen nativa continua. O helper Falcon e ICE netplay estão desativados no primeiro build experimental, para isolar a compatibilidade do renderizador e motor; o código dos mods é mantido. O código-fonte gerado requer a ROM específica legalmente adquirida.
