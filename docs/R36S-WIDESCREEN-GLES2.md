# R36S: widescreen / OpenGL ES 2.0 (ramo experimental)

## Status e referencia

Fonte estudada: https://github.com/mstan/SuperMarioWorldRecomp
- `docs/adaptive-renderer.md`: host renderer com cena nativa 256x224 e viewport amplo.
- `src/smw_renderer.c`: raster VRAM/OAM e compositor fora da janela original.
- `src/smw_renderer_hooks.c`: hooks do CPU recompilado para sprites e spawn.

**IMPORTANTE: Esta versao NAO implementa ainda o widescreen real daquele
repositorio.** A base snesrev/smw possui um PPU de 256x224 e executa logica
reimplementada em C, ao contrario dos hooks 65816 recompilados do mstan.
Portar o renderer dele exige adaptar esses hooks, a captura por scanline e
coordenadas de sprites no nosso motor. Apenas esticar/cortar a imagem
nao atende ao objetivo e nao sera confundido com widescreen real.

Este ramo adiciona SOMENTE a infraestrutura de apresentacao:
- `ViewportMode = 4:3` por padrao no R36S.
- `ViewportMode = 16:9` experimental: prepara a janela 16:9,
  mas a imagem do jogo continua nativa em 4:3, centralizada e SEM
  mostrar cenario extra. Em uma tela 4:3, isso significa barras pretas.
- `OutputMethod = SDL-Software` por padrao, como na build estavel.
- `OutputMethod = OpenGLES2` opcional, com `smw-gles2` separado.
  GLES2 usa `#version 100` (GLSL ES 1.00) e apenas recursos ES 2.0;
  nao requer VAO, `#version 330` ou OpenGL desktop 3.3.
- O executavel software `smw` nao vincula `libGLESv2` nem `libEGL`.
- Input START/SELECT, menu de sair, logs e saves preservados.

## Uso

Edite `/roms/ports/smw-r36s/smw.ini`:

```ini
[Graphics]
ViewportMode = 4:3
OutputMethod = SDL-Software
```

Para testar o contexto GLES2 (apenas se as bibliotecas/driver existirem):

```ini
[Graphics]
ViewportMode = 4:3
OutputMethod = OpenGLES2
```

O launcher escolhe `smw-gles2` se ele existir e suas bibliotecas
estiverem presentes. Caso contrario usa `smw` em SDL-Software.
Se a criacao de contexto EGL/GLES falhar, volte ao SDL-Software.
A compatibilidade efetiva depende do driver do DarkOSRE, nao apenas
do fato de o SoC teoricamente suportar ES2.

Para experimentar o layout 16:9 sem mudar a logica de SMW:

```ini
[Graphics]
ViewportMode = 16:9
OutputMethod = SDL-Software
```

Nao use `OutputMethod=OpenGL` no R36S: o renderizador desktop
existente exige OpenGL 3.3. Use `SDL-Software` ou `OpenGLES2`.
Nao ha ganho de visibilidade de fases com `ViewportMode=16:9`
enquanto o compositor adaptativo nao for portado.

## Plano tecnico do widescreen real

1. Introduzir um framebuffer de 342x224 ao selecionar 16:9 e manter
   256x224 quando 4:3, sem aumentar a estrutura de savestate PPU.
2. Capturar VRAM, paleta, OAM, scroll e estado de scanline/HDMA sincronizados.
3. Reconstruir tiles do nivel a partir dos dados Map16 do motor snesrev
   para fora da area nativa. Tratar BG1/BG2, scroll e parallax.
4. Capturar coordenadas mundiais de sprites e ownership dos OAM slots;
   desenhar sprites fora da viewport original sem wrapping de 8 bits.
5. Ajustar spawn/despawn opcional (modo original 4:3 ou por area visivel)
   sem alterar a gameplay/entrada/saida dos checkpoints.
6. Reancorar HUD (vida/bonus esquerda, reserva centro, tempo/moedas direita).
7. Validar transicoes, mapa, telas de titulo, castelos, boss, pipes,
   cenas especiais, saves e travamentos no R36S real.
8. Entregar o compositor com o *mesmo* backend SDL software e GLES2,
   evitando qualquer dependencia de OpenGL 3.3.

Somente depois de concluido e testado o passo acima a opcao
16:9 representara widescreen real. No momento trata-se de uma
**branch experimental / primeira etapa**, nao substituta da versao estavel.
