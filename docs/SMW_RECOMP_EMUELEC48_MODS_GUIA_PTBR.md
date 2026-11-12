# Guia de mods — Super Mario World Recomp no EmuELEC 4.8 (ARM64)

**Data:** 12/11/2026. **Status:** arquivos de mods presentes no pacote ARM64;
interface do launcher e execução dos mods **ainda não testadas em um aparelho
com EmuELEC 4.8**. O requisito GLIBC foi corrigido na compilação privada
`#43260992099` (GLIBC_2.34), mas isso não certifica SDL2, EGL/GLES2, controle,
interface e funcionamento do jogo/mods no aparelho.

## O que são os mods?

São **recursos integrados ao motor de recompilação**, não patchs IPS aplicados
à ROM. Cada recurso tem um catálogo `manifest.toml` em
`mods/preloaded/packages/<id>/<versão>/manifest.toml`. O usuário ativa os
recursos pelo **launcher > Mods**. O motor mantém a ROM USA original intacta,
aplica os recursos em tempo de execução e armazena preferências de forma
persistente. As opções dos mods não são os antigos campos
`Widescreen`/`WidescreenHud` do `config.ini`.

No pacote ARM64, esses cinco catálogos estão presentes:

| Mod | Padrão do manifest | O que faz | Instruções |
| --- | --- | --- | --- |
| SMW Adaptive Widescreen | Ativado | Expande o cenário horizontalmente; HUD adaptado, proporções de 4:3 até 100:9 | Abra **Mods > SMW Adaptive Widescreen**, escolha **Aspect ratio** e **Enemy spawn behavior** |
| SMW Native Co-op (Experimental) | Desativado | Mario e Luigi jogam **juntos na mesma fase** | Atribua controles aos jogadores 1 e 2; em **Mods**, ative **Simultaneous co-op (Experimental)**; pressione **Play**; no menu original selecione **2 Player** |
| Super Mario World MSU-1 | Desativado | Trilha PCM externa com áudio de qualidade superior | Ative **MSU-1 Audio** e forneça pacote **compatível com o mapa de faixas de Conn**; sem PCM o som permanece SPC original |
| Smash Bros 64 (Experimental) | Desativado | Experimenta substituir Mario por Captain Falcon | Na versão desktop, ative o recurso, selecione uma ROM própria de **Super Smash Bros. (USA) v1.0** para gerar os recursos e pressione Play. **No nosso ARM64, o helper automático de Falcon foi desativado na compilação: não presumir funcionamento** |
| SMW Playtest Diagnostics | Desativado | Captura inputs, estados e checksums para diagnóstico | Ative **Diagnostic recording** apenas durante investigação; após jogar, examine `logs/smw-replay-*` e seus arquivos auxiliares |

**Aviso:** presets visuais em `assets/shaders/` também foram copiados, mas
não são os cinco mods acima. Esses presets e a UI de filtros ainda precisam
de validação no GLES2 do EmuELEC.

## Primeiro teste com EmuELEC

1. Extraia o artifact `SMWRecomp-EmuELEC48-ARM64-GLES2-GLIBC-CHECKED`
   em `/storage/roms/ports/`. O ZIP contém `SMWRecomp.sh` e a pasta
   `SMWRecomp/`.
2. Copie sua ROM original `smw.sfc` para
   `/storage/roms/ports/SMWRecomp/smw.sfc`. Ela **não está no ZIP**.
3. Execute `SMWRecomp.sh` no EmuELEC e, **se o launcher abrir**,
   selecione a ROM e acesse a aba **Mods**. Na primeira execução,
   o launcher deve perguntar pela ROM ou usar a seleção em `rom.cfg`.
4. Para a primeira validação, deixe só o **Adaptive Widescreen** e
   configure **Aspect ratio = 4:3** (ou Fit to screen para TV widescreen)
   e **Enemy spawn behavior = Original 4:3**. Após testar imagens,
   áudio e controle, experimente `16:9` e `Screen-based`.
5. Ative co-op somente depois de confirmar controles individuais; o
   modo experimental guarda saves de co-op separadamente.
6. Se os mods não aparecerem ou a interface travar, **não copie DLLs
   nem bibliotecas do Ubuntu** para o sistema. Verifique
   `/storage/roms/ports/SMWRecomp/smw-emuelec.log`.

**Observação:** o primeiro-run, UI do launcher, gravação de estado de mods
e cada recurso só foram documentados/testados no projeto desktop original;
este guia **não é certificação** de funcionamento no EmuELEC.

## Persistência / arquivos

- Mods pré-instalados: `SMWRecomp/mods/preloaded/packages/`.
- Preferências de mods do projeto original: `mods/preloaded/state.toml`.
  Não edite esse TOML manualmente até termos confirmado o formato gerado
  pelo nosso binário no aparelho.
- Preferências gerais e binds: `config.ini`, `keybinds.ini` ao lado
  do executável, quando o programa conseguir gravá-los.
- Saves normais: `saves/`. Saves de co-op: `saves/native-coop-v1/`.
- Log do lançador EmuELEC: `smw-emuelec.log` na pasta `SMWRecomp/`.

## O que está implementado, mas ainda NÃO validado no EmuELEC

- Menu **Mods**, navegação com gamepad, persistência das opções.
- Widescreen dinâmico e efeitos gráficos em GPU do aparelho real.
- Dois jogadores com gamepads distintos.
- MSU-1 PCM externo no áudio do dispositivo.
- Captação de replay/diagnóstico com permissões de escrita.
- Captain Falcon, pois o helper gerador de recursos da ROM de Smash
  não foi incluído nessa build ARM64.

## Referências oficiais do código-base

- [README do motor mstan/SuperMarioWorldRecomp](https://github.com/mstan/SuperMarioWorldRecomp#readme)
  (seções *Widescreen*, *Experimental native simultaneous co-op*,
  *MSU-1 audio* e *Quick start*).
- [Widescreen adaptativo — detalhes](https://github.com/mstan/SuperMarioWorldRecomp/blob/main/docs/adaptive-renderer.md).
- [Co-op nativo — detalhes](https://github.com/mstan/SuperMarioWorldRecomp/blob/main/docs/NATIVE_COOP.md).
- [Guia atual da compilação ARM64 na nuvem](SMW_RECOMP_EMUELEC48_CLOUD.md).
