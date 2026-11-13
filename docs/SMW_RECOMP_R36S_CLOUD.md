# SMW Recomp R36S — ARM64 SDL2 OpenGL ES 2.0 (PortMaster experimental)

## Falha apos recadastro aceito: investigar hora da VM (12/11/2026)

Log do usuario (nao publicar codigos de autenticacao):
- `gh auth login` validou login;
- `config.sh --replace` respondeu `Successfully replaced the runner`;
- `svc.sh start` deixou listener ativo apenas ~3s;
- apos `Connected to GitHub`, `Failed to create a session. The runner registration has been deleted from the server`;
- GitHub CLI retornou runner `kali-r36s-kali: offline` em 5 consultas.

**Nova hipotese prioritaria: DESVIO DE RELOGIO (CLOCK SKEW), nao exclusao real.**
Problema confirmado em issues oficiais do projeto:
- https://github.com/actions/runner/issues/4648 (2026; Linux systemd e NTP tardio)
- https://github.com/actions/runner/issues/2967 (relatos de correção de hora em VMs)
- https://github.com/orgs/community/discussions/50255
Tokens OAuth com horarios errados produzem exatamente o texto enganoso.
Nao deduzir desvio apenas pelo timezone EST; comparar timestamps UTC
convertidos em epoch (fusos diferentes sao validos).

**Script preparado e validado sintaticamente**
[`CORRIGIR_HORA_RUNNER_KALI.sh`](../cloud-kit/r36s/CORRIGIR_HORA_RUNNER_KALI.sh);
[CI #43346875007](https://github.com/dehalbuq/smw/actions/runs/43346875007) PASS.

No Kali, como `smwrunner`:
```bash
curl -fL https://raw.githubusercontent.com/dehalbuq/smw/main/cloud-kit/r36s/CORRIGIR_HORA_RUNNER_KALI.sh -o CORRIGIR_HORA_RUNNER_KALI.sh
bash CORRIGIR_HORA_RUNNER_KALI.sh
```

Script calcula desvio entre UTC Kali e cabecalho HTTPS Date de api.github.com.
Se >30 segundos, aciona NTP via timedatectl/chrony, testa novamente e so
entao reinicia o servico existente, SEM novo login GitHub ou re-registro.
Retorna resumo seguro `TIME_DRIFT_SECONDS`, `RUNNER_SYSTEMD_ACTIVE`,
`RUNNER_KALI_ONLINE`, e indicadores resumidos de diagnostico OAuth.
Se desvio >30 persistir, corrigir hora do **Windows host** e Guest Additions
VirtualBox, ou verificar acesso NTP; nao expor credentials/OTP nem dump cru.

**Observacao:** o build privado #43343110703 ainda estava `queued` na
ultima consulta. Nao afirmar que o runner foi corrigido ou que o ZIP
foi gerado. Se clock skew nao for causa, proxima investigacao:
conflito de identidade duplicada (`--replace`), recursos do GitHub
API `repos/dehalbuq/smw-rom-private/actions/runners`, diagnosticos
`_diag/Runner_*.log` (sanitizados), registro com nome unico.

## Recuperacao do runner Kali com registro removido (12/11/2026)

O usuario compartilhou `systemd` mostrando que a VM conecta ao GitHub,
mas o listener encerra com
`Failed to create a session. The runner registration has been deleted from the server, please re-configure`.
A tela `Active: active (running)` 27ms apos `svc.sh start` nao prova
que o servico permaneceu conectado. A compilacao privada
[#43343110703](https://github.com/dehalbuq/smw-rom-private/actions/runs/43343110703)
continuava `queued` quando checada.

Um script publico de reparo foi adicionado:
[`cloud-kit/r36s/RECUPERAR_RUNNER_KALI.sh`](../cloud-kit/r36s/RECUPERAR_RUNNER_KALI.sh).

Executar **no Kali** como usuario `smwrunner`:
```bash
curl -fL https://raw.githubusercontent.com/dehalbuq/smw/main/cloud-kit/r36s/RECUPERAR_RUNNER_KALI.sh -o RECUPERAR_RUNNER_KALI.sh
bash RECUPERAR_RUNNER_KALI.sh
```

O script para/desinstala apenas o serviço runner, faz backup
restrito dos arquivos locais `.runner`, `.credentials` e
`.credentials_rsaparams`, pede autorizacao GitHub em ambiente
temporario (`GH_CONFIG_DIR`, com `--insecure-storage`), solicita
novo registration-token via GitHub API, registra somente no repo
privado com label `r36s-kali`, reinicia servico e consulta se aparece
`online`. **Nao** reinstala o Kali, nao apaga a pasta `_work` e
nao expoe SSH ou credenciais ao chat. Teste de sintaxe publica em
[`r36s-runner-recovery-check.yml`](../.github/workflows/r36s-runner-recovery-check.yml).

Se o runner permanecer offline, coletar
`sudo journalctl --no-pager -n 40 -u actions.runner.dehalbuq-smw-rom-private.kali-r36s-kali.service`
sem expor segredos. Nao considerar o workflow aprovado ate constar
`completed: success` e artefato sem ROM.

## Fase Kali acelerada - compilacao cruzada nativa x86_64 para ARM64 (12/11/2026)

**Ultima falha:** segundo attempt do [Kali #43331876649](https://github.com/dehalbuq/smw-rom-private/actions/runs/43331876649)
chegou a **96%** e falhou em
`recomp-ui/src/common/backends/imgui/launcher_imgui.cpp:12525`:
`SDL_OpenURL was not declared in this scope`. Debian Buster usa SDL2 2.0.9,
anterior a `SDL_OpenURL` (SDL 2.0.14). O build nao falhou por falta de
CPU ou RAM. A recompilacao ARM64 dentro de QEMU demorava excessivamente.

**Correcao principal de performance:** abandonar QEMU para o GCC.
Rodar um Docker **amd64 nativo no Kali x86_64** com toolchain
`aarch64-linux-gnu-gcc/g++` e libs ARM64 multiarch do Debian Buster.
O executavel produzido continua ELF AArch64 GLIBC<=2.30 para R36S.
Arquivos novos:
- [`Dockerfile.cross-buster-x64`](../cloud-kit/r36s/Dockerfile.cross-buster-x64)
- [`toolchain-aarch64-buster.cmake`](../cloud-kit/r36s/toolchain-aarch64-buster.cmake)
- [`r36s-cross-buster-preflight.yml`](../.github/workflows/r36s-cross-buster-preflight.yml)

**Testes publicos ja PASSARAM, sem ROM:**
- [#43342742106](https://github.com/dehalbuq/smw/actions/runs/43342742106):
  compilador cruzado x86->ARM64, link SDL2/EGL/GLES2 e verificacao de
  versoes GLIBC do ELF gerado.
- [#43343324382](https://github.com/dehalbuq/smw/actions/runs/43343324382):
  configuracao CMake original e **15 modulos reais** da engine (SDL2/GLES2,
  widescreen, co-op, launcher) compilados com o cross GCC nativo.

**Compatibilidade SDL:** o
[`build-and-package.sh`](../cloud-kit/r36s/build-and-package.sh)
aplica patch verificado que envolve `SDL_OpenURL` com
`#if SDL_VERSION_ATLEAST(2,0,14)`; no SDL2 2.0.9 nao tenta abrir
URL externa e conserva o resto da UI e jogo. Preserva os dois patches Python
3.7 para hooks de renderer e co-op.

**Workflow privado Kali atualizado:**
[`smw-r36s-kali-selfhosted.yml`](https://github.com/dehalbuq/smw-rom-private/blob/main/.github/workflows/smw-r36s-kali-selfhosted.yml)
commit `79d93a2646c8f667dd8c5b0a0b9ee67784bcae90`. Ele avalia
`nproc`, MemAvailable e usa `JOBS = min(nproc, MemAvailable_MiB/1200)`
com minimo de 1, e `ccache` persistente em
`~/.cache/smw-r36s-ccache` (maximo 6GB) para evitar compilar tudo
do zero ao corrigir futuros erros. O QEMU nao executa mais compiladores,
apenas continua disponivel como ferramenta opcional de diagnostico.

**Execucao:** [#43343110703](https://github.com/dehalbuq/smw-rom-private/actions/runs/43343110703)
criada automaticamente, **ainda queued no ultimo exame**, portanto
**nao ha ZIP aprovado nem tempo/velocidade medidos no Kali**.
Se nao iniciar, deixar a VM VirtualBox ligada, confirmar
`sudo ~/actions-runner-smw-r36s/svc.sh status` como `smwrunner`
ou revisar runner em Settings/Actions/Runners. Nao declarar sucesso
sem job concluido e artefato valido.

## Segunda falha real / Python 3.7 co-op hooks (12/11/2026)

- [Segunda tentativa Kali #43331876649](https://github.com/dehalbuq/smw-rom-private/actions/runs/43331876649)
  (attempt 1) falhou ao gerar `smw_renderer_hooks.stamp` por
  `tools/apply_coop_hooks.py:70`:
  `TypeError: write_text() got an unexpected keyword argument 'newline'`.
- O patch anterior do renderer **passou** e imprimiu
  `SMW host hooks: 23 sites, 13 banks updated`. A falha do cooperativo
  vinha da mesma API Python incompatível com o Buster.
- Corrigido `cloud-kit/r36s/build-and-package.sh` para aplicar
  **ambos** os patches exatos antes da compilação e verificar a sintaxe
  `compile(..., 'exec')`, com âncoras específicas e fail-fast para drift.
  Commit: `6f5503e08ae36175b5030e7366e318289e9f4828`.
- Reexecução do job com `rerun_failed_workflow_run_jobs` na **attempt 2**
  do mesmo run #43331876649. O workflow clona o port público no início,
  portanto consome a correção nova no início da execução.
- Importante: esperar conclusão explícita antes de declarar ZIP pronto.
  Revisar `r36s-compile.log` caso surjam erros posteriores.

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
