<#
.SYNOPSIS
    Envia sua ROM original smw.sfc para um repositorio GitHub PRIVADO.
.DESCRIPTION
    Windows PowerShell 5.1 / PowerShell 7. Requer git e GitHub CLI (gh).
    Cria repositorio se necessario, verifica privacidade, confere SHA256,
    envia smw.sfc por Git e configura o nome do repo no workflow publico.
    NAO grava tokens em arquivos, NAO altera repositorio publico com a ROM.
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ENVIAR_ROM_PRIVADA_WINDOWS.ps1 -RomPath "D:\ROMs\Super Mario World (USA).sfc"
.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File .\ENVIAR_ROM_PRIVADA_WINDOWS.ps1 -RomPath "D:\ROMs\smw.sfc" -SubstituirRomExistente
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string] $RomPath,

    [string] $PrivateRepo = 'dehalbuq/smw-rom-private',

    [string] $WorkflowRepo = 'dehalbuq/smw',

    [switch] $SubstituirRomExistente
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ExpectedSha256 = '0838e531fe22c077528febe14cb3ff7c492f1f5fa8de354192bdff7137c27f5b'

function Testar-ExitCode {
    param([string] $Descricao)
    if ($LASTEXITCODE -ne 0) {
        throw ("Falha: {0} (exit code {1})." -f $Descricao, $LASTEXITCODE)
    }
}

function Verificar-Comando {
    param([string] $Nome)
    if (-not (Get-Command $Nome -ErrorAction SilentlyContinue)) {
        throw ("Nao encontrei '{0}'. Instale Git for Windows e GitHub CLI (gh) antes de continuar." -f $Nome)
    }
}

Write-Host '==============================================' -ForegroundColor Cyan
Write-Host ' SMW: ROM original -> GitHub PRIVADO' -ForegroundColor Cyan
Write-Host '==============================================' -ForegroundColor Cyan

if ($PrivateRepo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    throw 'PrivateRepo deve ter o formato usuario/nome-do-repo.'
}
if ($WorkflowRepo -notmatch '^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$') {
    throw 'WorkflowRepo deve ter o formato usuario/nome-do-repo.'
}
if ($PrivateRepo.ToLowerInvariant() -eq $WorkflowRepo.ToLowerInvariant()) {
    throw 'Protecao: o repositorio privado NAO pode ser o repositorio do workflow.'
}
if (-not (Test-Path -LiteralPath $RomPath -PathType Leaf)) {
    throw ("Arquivo da ROM nao encontrado: {0}" -f $RomPath)
}

Verificar-Comando 'git'
Verificar-Comando 'gh'

$ResolvedRom = (Resolve-Path -LiteralPath $RomPath -ErrorAction Stop).ProviderPath
$HashLocal = (Get-FileHash -LiteralPath $ResolvedRom -Algorithm SHA256 -ErrorAction Stop).Hash.ToLowerInvariant()
$RomBytes = (Get-Item -LiteralPath $ResolvedRom -ErrorAction Stop).Length
Write-Host ("ROM encontrada: {0} bytes" -f $RomBytes)
Write-Host ("SHA256: {0}" -f $HashLocal)
if ($HashLocal -ne $ExpectedSha256) {
    throw ('A ROM nao corresponde ao SMW USA exigido pelo upstream. ' +
           'Use a sua copia correta, sem cabecalho extra. Nada foi enviado.')
}
Write-Host '[OK] SHA256 confirmado.' -ForegroundColor Green

& gh auth status --hostname github.com
Testar-ExitCode 'verificar autenticacao gh'
& gh auth setup-git --hostname github.com
Testar-ExitCode 'configurar autenticacao do Git via gh'

# Uma falha ao consultar pode significar que o repo ainda nao existe.
# Mesmo nesse caso, validamos a privacidade DEPOIS de criar/consultar.
$PreferenciaAnterior = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $PrivateFlag = & gh repo view $PrivateRepo --json isPrivate --jq '.isPrivate' 2>$null
    $RepoExiste = ($LASTEXITCODE -eq 0)
}
finally {
    $ErrorActionPreference = $PreferenciaAnterior
}

if (-not $RepoExiste) {
    Write-Host ("Criando repositorio PRIVADO: {0}" -f $PrivateRepo) -ForegroundColor Yellow
    & gh repo create $PrivateRepo --private --description 'ROM pessoal para compilacao privada do SMW Recomp'
    Testar-ExitCode 'criar repositorio privado no GitHub'
}

$PrivateFlag = & gh repo view $PrivateRepo --json isPrivate --jq '.isPrivate'
Testar-ExitCode 'verificar privacidade do repositorio'
if (("$PrivateFlag").Trim().ToLowerInvariant() -ne 'true') {
    throw ('BLOQUEADO: ' + $PrivateRepo + ' nao e PRIVADO! A ROM NAO sera enviada.')
}
Write-Host ("[OK] Repositorio confirmado PRIVADO: {0}" -f $PrivateRepo) -ForegroundColor Green

$TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ('smw-rom-private-' + [guid]::NewGuid().ToString('N'))
$OldPrompt = $env:GIT_TERMINAL_PROMPT
try {
    $env:GIT_TERMINAL_PROMPT = '0'
    Write-Host 'Preparando clone temporario do repositorio privado...'
    & git clone --quiet --depth 1 ("https://github.com/{0}.git" -f $PrivateRepo) $TempDir
    Testar-ExitCode 'clonar repositorio privado'

    $Destino = Join-Path $TempDir 'smw.sfc'
    $PularUpload = $false
    if (Test-Path -LiteralPath $Destino -PathType Leaf) {
        $HashExistente = (Get-FileHash -LiteralPath $Destino -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($HashExistente -eq $ExpectedSha256) {
            Write-Host '[OK] A ROM correta ja esta no repositorio privado.' -ForegroundColor Green
            $PularUpload = $true
        }
        elseif (-not $SubstituirRomExistente) {
            throw ('Ja existe smw.sfc com outro SHA256 no repositorio privado. ' +
                   'Para substituir intencionalmente, execute com -SubstituirRomExistente.')
        }
    }

    if (-not $PularUpload) {
        Copy-Item -LiteralPath $ResolvedRom -Destination $Destino -Force -ErrorAction Stop
        $HashCopiado = (Get-FileHash -LiteralPath $Destino -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($HashCopiado -ne $ExpectedSha256) {
            throw 'SHA256 nao confere depois da copia. Upload cancelado.'
        }
        & git -C $TempDir add -- smw.sfc
        Testar-ExitCode 'adicionar SOMENTE smw.sfc'
        & git -C $TempDir -c user.name='SMW ROM Private Upload' -c user.email='upload@users.noreply.github.com' commit -m 'Add user-owned SMW USA ROM for private cloud compilation'
        Testar-ExitCode 'criar commit privado da ROM'
        & git -C $TempDir push --quiet -u origin HEAD
        Testar-ExitCode 'enviar commit para o GitHub privado'
        Write-Host '[OK] Upload concluido no repositorio PRIVADO!' -ForegroundColor Green
    }
}
finally {
    $env:GIT_TERMINAL_PROMPT = $OldPrompt
    if (Test-Path -LiteralPath $TempDir) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}

# Confere mais uma vez a privacidade depois do push.
$PrivateFlag = & gh repo view $PrivateRepo --json isPrivate --jq '.isPrivate'
Testar-ExitCode 'confirmar privacidade apos o upload'
if (("$PrivateFlag").Trim().ToLowerInvariant() -ne 'true') {
    throw 'ATENCAO: privacidade mudou! Verifique o repositorio imediatamente.'
}

Write-Host 'Configurando SMW_PRIVATE_ROM_REPO no repositorio do workflow...'
& gh secret set SMW_PRIVATE_ROM_REPO --repo $WorkflowRepo --body $PrivateRepo
if ($LASTEXITCODE -eq 0) {
    Write-Host '[OK] Secret SMW_PRIVATE_ROM_REPO configurado.' -ForegroundColor Green
}
else {
    Write-Warning ('Upload privado OK, mas nao consegui definir SMW_PRIVATE_ROM_REPO. ' +
                   'Configure esse secret manualmente em ' + $WorkflowRepo)
}

Write-Host ''
Write-Host '==============================================' -ForegroundColor Green
Write-Host ' ROM guardada no repositorio PRIVADO!' -ForegroundColor Green
Write-Host '==============================================' -ForegroundColor Green
Write-Host ("Repositorio: https://github.com/{0}" -f $PrivateRepo)
Write-Host ''
Write-Host 'FALTA APENAS O TOKEN DE LEITURA PARA O WORKFLOW:' -ForegroundColor Yellow
Write-Host '1. Crie um fine-grained PAT restrito SOMENTE a esse repositorio privado.'
Write-Host '   Permissao: Repository permissions -> Contents -> Read-only.'
Write-Host ("2. Configure o secret SMW_PRIVATE_ROM_TOKEN em: https://github.com/{0}/settings/secrets/actions" -f $WorkflowRepo)
Write-Host '3. Execute Actions -> SMW Recomp EmuELEC 4.8 ARM64 - Cloud -> Run workflow -> full.'
Write-Host ''
Write-Host 'Nunca cole o PAT no chat nem no codigo do repositorio.' -ForegroundColor Yellow
