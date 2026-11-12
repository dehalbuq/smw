# SMW Recomp R36S — ARM64 SDL2 OpenGL ES 2.0 (PortMaster experimental)

**Projeto separado do port SMW original baseado em snesrev.**
Não substituir nem renomear o binário/launcher do port anterior.

## Histórico do trabalho, em 12/11/2026

- O projeto é baseado em `mstan/SuperMarioWorldRecomp`; preserva
  `SMW Adaptive Widescreen`, `SMW Native Co-op`, controle e assets de mods.
  O helper gerador do Falcon e ICE netplay foram desativados para diminuir
  dependências; o manifesto dos mods não comprova funcionamento.
- A tela do R36S é 640x480 4:3; o launcher usa `config.ini` com
  `WindowSize = 640x480`, `Fullscreen = 1`,
  `OutputMethod = OpenGL` (apresentador GLES2), filtro linear desligado.
- PortMaster identifica ArkOS/R36S com **GLIBC 2.30**;
  o artefato do EmuELEC compilado no Ubuntu 22.04 exige **GLIBC 2.34**,
  portanto **não pode ser reutilizado**.
- **Toolchain pronta:** Docker Debian Buster AArch64
  **GLIBC 2.28**, CMake 3.25.2, SDL2 2.0.9, GCC8.
  [Teste sem ROM #43269480908](https://github.com/dehalbuq/smw/actions/runs/43269480908) **PASS**.
- **Motor sem ROM aprovado:** [GitHub Actions #43270639694](https://github.com/dehalbuq/smw/actions/runs/43270639694)
  **SUCCESS**, CMake reconheceu 205 unidades e **15 fontes reais ARM64**
  compilaram com SDL2/GLES2/glibc 2.28, preservando launcher, widescreen e co-op.
  Foi usado um arquivo sintético apenas para satisfazer a lista de fontes no
  CMake; esse teste **não gera jogo jogável**.
- **Compilação COMPLETA** está definida em
  [workflow privado](https://github.com/dehalbuq/smw-rom-private/blob/main/.github/workflows/smw-r36s-private-aarch64.yml):
  usa ROM do repositório privado (SHA256 verificado), recompiler Rust no host ARM64,
  elimina ROM antes da etapa Docker, compila gerado C no Buster, exige GLIBC<=2.30,
  empacota na pasta `smwrecompr36s/` e envia apenas artifact PRIVADO sem ROM.
- **BLOQUEIO ATUAL:** [execução privada #43269677656](https://github.com/dehalbuq/smw-rom-private/actions/runs/43269677656)
  falhou **antes de iniciar qualquer etapa**; API do GitHub
  mostra `steps: []`, `runner_id: 0`. A repetição também falhou.
  O teste mínimo de runner x86-64 sem ROM
  [#43270259518](https://github.com/dehalbuq/smw-rom-private/actions/runs/43270259518)
  também ficou sem runner. Portanto **não é erro do código nem da ROM**,
  mas a causa da falha de alocação ainda não foi diagnosticada.
  Conferir a mensagem em Actions e as configurações
  Settings > Actions > General e Billing and licensing > Usage/Budgets.
  Não declarar um artifact R36S pronto antes de o workflow privado concluir.

## Estrutura planejada do ZIP

```text
SMW Recomp R36S.sh
port.json
gameinfo.xml
README.md
smwrecompr36s/
  SuperMarioWorldSNESRecomp
  config.ini
  diagnose_r36s.sh
  ABI-REPORT.txt
  assets/
  mods/
  licenses/
  smw.sfc             <- usuário copia a ROM original; NÃO será incluída no ZIP
```

Instale apenas em `/roms/ports` ou `/roms2/ports`, sem alterar a
versão original. PortMaster fornece `control.txt` e `gptokeyb`;
o launcher chama `get_controls`, `pm_platform_helper` e
`gptokeyb` para hotkey+Start (normalmente Select+Start).
Se esses componentes não existirem, o jogo ainda poderá abrir,
mas o atalho e a leitura de controles precisarão de teste.

## Fontes do port e scripts

- [Dockerfile Buster](../cloud-kit/r36s/Dockerfile.buster-arm64)
- [Launcher PortMaster R36S](../cloud-kit/r36s/SMW%20Recomp%20R36S.sh)
- [Build/package](../cloud-kit/r36s/build-and-package.sh)
- [Config 4:3](../cloud-kit/r36s/config.ini)
- [Diagnóstico R36S](../cloud-kit/r36s/diagnose_r36s.sh)
- [Workflow público sem ROM](../.github/workflows/r36s-buster-preflight.yml)
- [Workflow privado com ROM](https://github.com/dehalbuq/smw-rom-private/blob/main/.github/workflows/smw-r36s-private-aarch64.yml)

## Próxima ação

Resolver a falta de runner no repositório PRIVADO e reexecutar workflow
R36S no GitHub. Inspecionar logs dos arquivos gerados, aplicar correções
sem tocar no port snesrev original. Só depois da conclusão confirmar o
máximo `GLIBC_` no ELF, dependências SDL2/EGL/GLES e testar no
dArkOSRE/ArkOS4Clone reais. Não prometer FPS ou boot até hardware testado.

Referências: [PortMaster device info](https://github.com/PortsMaster/PortMaster-Info/blob/main/device_info.json)
e [PortMaster packaging](https://portmaster.games/contribute/porting/packaging/).
