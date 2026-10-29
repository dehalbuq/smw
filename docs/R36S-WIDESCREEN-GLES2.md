# R36S: widescreen / OpenGL ES 2.0 (ramo experimental)

## Marco experimental 2 - composicao inicial do mundo horizontal (29/10/2026)

**NOVO:** ao selecionar `ViewportMode = 16:9`, o host agora aloca
342x224 e tenta reconstruir **tiles reais da fase** nas regioes fora
do PPU original de 256x224, lendo Map16 da RAM do motor snesrev, tiles
da VRAM e paletas. Isso substitui o prototipo anterior que somente
centralizava o 4:3.

O framebuffer original nao foi alterado: seu trecho de 256x224 e
copiado integralmente. Proximo ao inicio/fim da fase, a posicao da
imagem nativa e limitada ao terreno real, evitando desenhar mundo
com coordenadas negativas ou apos o ultimo screen.

**Limites desta primeira fase (nao e widescreen completo):**
- Ativo so durante jogo em fases horizontais com PPU mode 1 e ROM
  de comparacao disponivel no `smw_assets.dat`. Titulo, mapa, bosses,
  fases verticais, efeitos especiais ou cenas de outros modos usam
  fallback 4:3 com fundo preto.
- Sprite spawn, OAM de objetos fora da tela, hud reancorado,
  transparencia e efeitos de color math / HDMA ainda nao foram
  portados. Terreno e fundos podem ter cores/prioridade incorretas,
  tiles ausentes ou artefatos de rolagem.
- O codigo testa dados e estrutura, mas ainda depende de teste
  visual e de desempenho no R36S fisico.
- **NUNCA substituir a build principal**: teste apenas esta branch.
- No log `r36s-diagnostic.log` procure `[WIDE_SCENE]`;
  `expand=1` significa que o compositor expandido foi acionado.
  `expand=0` informa cena sem suporte ou ROM ausente.

Para testar:
```ini
[Graphics]
ViewportMode = 16:9
OutputMethod = OpenGLES2
```
4:3 + SDL-Software continuam sendo as definicoes padrao e
funcionais. Para voltar, mude `ViewportMode=4:3` e reinicie.


## Status e referencia

### Licenciamento do codigo de referencia

O arquivo `LICENSE` do repositorio `mstan/SuperMarioWorldRecomp`
declara **PolyForm Noncommercial License 1.0.0**. A licenca de um
manifesto de mod nao substitui automaticamente a licenca dos arquivos
de renderizacao do repositorio. Esta etapa NAO copia os arquivos
`smw_renderer.c` / `smw_renderer_hooks.c` para o nosso fork.
Antes de distribuir uma incorporacao direta, analisar os termos
e obter autorizacao apropriada quando necessario. O design do ramo
visa ser independente e manter o codigo original do snesrev intacto.


Fonte estudada: https://github.com/mstan/SuperMarioWorldRecomp
- `docs/adaptive-renderer.md`: host renderer com cena nativa 256x224 e viewport amplo.
- `src/smw_renderer.c`: raster VRAM/OAM e compositor fora da janela original.
- `src/smw_renderer_hooks.c`: hooks do CPU recompilado para sprites e spawn.

**IMPORTANTE: Esta versao ainda NAO implementa o compositor widescreen
completo daquele repositorio.** A base snesrev/smw possui um PPU de 256x224 e executa logica
reimplementada em C, ao contrario dos hooks 65816 recompilados do mstan.
Portar o renderer dele exige adaptar esses hooks, a captura por scanline e
coordenadas de sprites no nosso motor. Apenas esticar/cortar a imagem
nao atende ao objetivo e nao sera confundido com widescreen real.

A infraestrutura de apresentacao e o renderizador inicial de Map16 agora incluem:
- `ViewportMode = 4:3` por padrao no R36S.
- `ViewportMode = 16:9` experimental: prepara a janela 16:9,
  gera a imagem de 342x224 e renderiza blocos de cenario extras somente
  em fases horizontais compativeis. Cenas sem suporte usam barras pretas.
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
Na build deste ramo, a extensao de cenario Map16 inicial esta ativa em fases
compativeis; sprites e demais efeitos ainda dependem de port adicional.

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

Depois da validacao visual, de sprites, HUD e efeitos, a opcao 16:9
podera ser considerada widescreen completo. No momento trata-se de uma
**branch experimental / primeira etapa**, nao substituta da versao estavel.
