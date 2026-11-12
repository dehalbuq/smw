# SMW Recomp R36S — ARM64 SDL2 OpenGL ES 2.0 (PortMaster experimental)

## Falha real do primeiro build completo e correcao (12/11/2026)

- [Execucao Kali #43295544908](https://github.com/dehalbuq/smw-rom-private/actions/runs/43295544908):
  **FAIL em 14%**, apos checkout privado, checksum ROM, Docker+QEMU,
  Rust/CPU 65816 regen e toolchain ARM64 Debian Buster passarem.
- Causa direta em `tools/apply_renderer_hooks.py:85`:
  `Path.write_text(changed, encoding='utf-8', newline='\\n')`
  levanta `TypeError: write_text() got an unexpected keyword argument 'newline'`
  no **Python 3.7** do Debian Buster. Nao indica erro do jogo nem da ROM.
- Corrigido em `cloud-kit/r36s/build-and-package.sh`: patch pontual,
  verificado por contagem exata, removendo apenas o parametro `newline`,
  que nao e necessario para LF no Linux.
  Commit publico: `f6a33740886d3b330ce3a9ecf186759397df08c9`.
- Diagnostico secundario: o container compilava como root e deixou
  arquivos da arvore CMake sem permissao para `smwrunner` apagar.
  O workflow novo usa `docker run --user UID:GID --env HOME=/tmp` para
  build e limpeza de pastas temporarias antigas via container isolado.
  Commit privado: `ec30085c5266d332184906e841738dcdc9ffdb33`.
- Novo workflow [#43331876649](https://github.com/dehalbuq/smw-rom-private/actions/runs/43331876649),
  disparado automaticamente pelo commit privado. **Nao concluir que passou
  ate conferir explicitamente o status e artefato.**
- Se a compilacao falhar em outro ponto, ler `r36s-compile.log` do job,
  corrigir o problema exato e reexecutar no runner Kali, sem necessidade
  de alterar o firmware do R36S.

## Kali Linux na VirtualBox — runner proprio do GitHub (12/11/2026)

**Objetivo:** compilar sem gastar minutos de runner hospedado pelo GitHub,
usando somente o repositorio privado `dehalbuq/smw-rom-private`.
Na data da configuracao, o GitHub Docs informa que runner self-hosted e gratuito
em repos privados; a mudanca de cobranca anunciada para marco de 2026 foi adiada.

**Instalador Kali x86-64:** [`INSTALAR_RUNNER_KALI.sh`](../cloud-kit/r36s/INSTALAR_RUNNER_KALI.sh)

Em uma VM Kali x86-64 com usuario normal (nao root), boa memoria, disco e
rede NAT; evite montar pasta Windows compartilhada:

```bash
sudo apt-get update && sudo apt-get install -y curl ca-certificates
curl -fL https://raw.githubusercontent.com/dehalbuq/smw/main/cloud-kit/r36s/INSTALAR_RUNNER_KALI.sh -o INSTALAR_RUNNER_KALI.sh
bash INSTALAR_RUNNER_KALI.sh
```

O instalador instala Docker, QEMU/binfmt, GitHub CLI, Rust, dependencias,
verifica QEMU AArch64 com `debian:buster` e registra a VM como runner
self-hosted **somente** para o repositorio privado com label `r36s-kali`.
Uma autorizacao interativa via `gh auth login --web` e necessaria; a
credencial usada para registro e temporaria, nao compartilhada com o chat.
O runner inicia como servico systemd.

**Workflow de build automatizado:** [`smw-r36s-kali-selfhosted.yml`](https://github.com/dehalbuq/smw-rom-private/blob/main/.github/workflows/smw-r36s-kali-selfhosted.yml)
usa `runs-on: [self-hosted, Linux, X64, r36s-kali]`. O codigo Rust recompila
o SNES usando ROM privada apenas na VM; o codigo C e compilado em Docker/QEMU
AArch64 Debian Buster GLIBC 2.28, e o pacote PortMaster sem ROM e colocado
como GitHub Action artifact privado. O checkout privado e copias da ROM sao
apagados no final, assim como fontes temporarias.

**Workflow criado e aguardando runner:** [#43295544908](https://github.com/dehalbuq/smw-rom-private/actions/runs/43295544908).
Trabalhos sem runner podem expirar apos 24 horas; nesse caso, execute
`Run workflow` novamente em Actions quando a VM estiver online.

**Seguranca:** o grupo Docker tem poder de administrador **dentro da VM**.
Nao habilitar runner no repositorio publico; nao montar particoes/pastas
de Windows; nao expor porta 22/SSH ao mundo; nao executar workflows de
contribuidores desconhecidos; manter a VM atualizada. Apenas workflows
escritos no repo privado devem executar no runner. A VM deve ter
recursos suficientes para Docker/QEMU e compilacao AArch64; desempenho
pode ser limitado por emulacao do CPU ARM64.

**Estado:** instalador e YAML publicados, mas nao ativados na VM do usuario;
nao existe binario R36S novo aprovado ainda. Compilacao completa e
testes de driver/controles no R36S continuam pendentes.


## Compilacao LOCAL no Linux (sem GitHub Actions) — preparado

Pode ser executada em Ubuntu 24.04 LTS ou Linux Mint 22 com CPU
**x86_64** (usa Docker + QEMU para compilacao AArch64) ou em Linux ARM64
nativo. O script baixa o codigo-fonte publico em checkout separado;
gera CPU-C com Rust a partir de **sua ROM local** e remove a copia
temporaria antes de compilar em Debian Buster AArch64 com GLIBC 2.28.

Script: [`cloud-kit/r36s/COMPILAR_SMW_R36S_LINUX.sh`](../cloud-kit/r36s/COMPILAR_SMW_R36S_LINUX.sh).

```bash
curl -fL https://raw.githubusercontent.com/dehalbuq/smw/main/cloud-kit/r36s/COMPILAR_SMW_R36S_LINUX.sh -o COMPILAR_SMW_R36S_LINUX.sh
bash COMPILAR_SMW_R36S_LINUX.sh preparar
bash COMPILAR_SMW_R36S_LINUX.sh compilar "/home/SEU_USUARIO/ROMs/smw.sfc"
```

- **Nao executar como root** o script inteiro; o instalador solicita sudo apenas
  para pacotes, Docker e permissoes de output.
- Na primeira compilacao, o Docker/QEMU ARM64 baixara os pacotes da
  distribuicao antiga; em PC x86_64 sera mais pesado que compilacao nativa.
- Para baixa memoria, execute `JOBS=1 bash COMPILAR_SMW_R36S_LINUX.sh compilar "/caminho/smw.sfc"`.
- **O ZIP previsto** apos build bem-sucedido ficara em
  `~/SMWRecomp-R36S-Local/SMWRecomp-R36S-ARM64-GLES2-GLIBC228.zip`.
  Os logs ficarao em `~/SMWRecomp-R36S-Local/logs/`.
- A ROM nao sera incorporada no ZIP. Colocar manualmente a ROM original
  `smw.sfc` na pasta `smwrecompr36s/` do SD depois do build.
- Nao alterar particoes, instalar outro sistema operacional ou modificar
  firmwares por meio desses scripts.
- **Importante:** este pipeline local foi criado e revisado, mas o
  executavel completo ainda nao foi produzido nem testado em hardware.
  Qualquer erro de compilacao exige revisar `logs/03-compilacao-r36s.txt`.
  CMake/15 fontes ja passaram na mesma toolchain em nuvem.


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
