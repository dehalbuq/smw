# SMW Recomp — build ARM64 SDL2/GLES2 100% no GitHub Actions

## Progresso confirmado em nuvem — 12/11/2026

**GLES2 estrito / renderizador real:** [GitHub Actions #43240431294](https://github.com/dehalbuq/smw/actions/runs/43240431294) — **PASS**.

- Arquitetura: ELF AArch64 (runner Ubuntu 24.04 ARM).
- API: `OpenGL ES 2.0 Mesa 25.2.8` usando `MESA_GLES_VERSION_OVERRIDE=2.0` (teste de perfil compatível com GLES2; não é teste de driver EmuELEC).
- Código de `src/port/gles2_renderer.c` compilado com `-Wall -Wextra -Werror`.
- Criou janela SDL2/EGL; compilou shaders, desenhou 3 quadros, verificou conversão BGRA, viewport, bordas e atualização de textura dinâmica com readback `glReadPixels`.
- Corrigida inicialização explícita do campo opcional `RendererFuncs.Reconfigure`.
- As contas de aspect ratio e spawning do motor real **não** foram exercitadas neste teste isolado: usamos stub de `SmwDestination`; a lógica do widescreen original permanece intacta.
- O jogo completo **ainda não foi compilado**: necessita da ROM original legalmente adquirida e do workflow `full`.
- A certificação binária EmuELEC 4.8 (glibc, EGL, SDL2 do firmware e driver GPU do aparelho) permanece pendente.

O código do port `dehalbuq/smw` voltado ao R36S não foi alterado; apenas `.github/workflows/`, `cloud-kit/` e este documento foram adicionados/atualizados.


Este laboratório fica **isolado** do motor snesrev e dos releases do R36S já existentes neste repositório. O workflow clona *mstan/SuperMarioWorldRecomp* em um diretório temporário e aplica o kit somente ali.

## Usar sem Kali, WSL ou compilação local

1. **O kit SDL2/GLES2 já está no GitHub**, em `cloud-kit/EmuELEC48_Kit.tar.xz.b64`; não precisa baixar ou enviar ZIP do ChatGPT.
2. Abra **Actions > SMW Recomp EmuELEC 4.8 ARM64 - Cloud > Run workflow**. Escolha `audit` para inspecionar o checkout original, extrair/verificar o kit embutido e aplicar os patches. Este modo não precisa de ROM.
3. Resultado confirmado do audit: [execução #43235960738](https://github.com/dehalbuq/smw/actions/runs/43235960738) — sucesso; SDL2/GLES2 patch aplicado ao checkout temporário e nenhum arquivo do motor snesrev alterado.

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
