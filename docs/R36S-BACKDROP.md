# Fondo ilustrado 4:3 pixel-perfect no R36S (SDL e GLES2)

O R36S 640x480 usa quadro SNES 256x224 ampliado para 512x448. A arte decorativa preenche os 64px laterais e 16px verticais que seriam pretos.

## Instalação

Copie background.png no mesmo diretório do smw.ini, normalmente /roms/ports/smw-r36s/smw-r36s/ quando usa o script de PortMaster. Preserve smw_assets.dat e saves.

### Arquivo smw.ini

    [Graphics]
    PixelPerfect = 1
    UseBackdrop = 1
    BackgroundImage = background.png

UseBackdrop = 0 desliga o fundo. PNG ausente ou inválido mantém bordas pretas, sem abortar o jogo. A imagem é carregada uma vez no início via stb_image (sem SDL2_image), enviada para uma textura de GPU no GLES2 ou SDL_Renderer.

A versão inicial redimensiona somente o fundo até a superfície física inteira: funciona em 4:3, 16:9 ou outras proporções, sem distorcer o quadro do jogo e sem mudar sua resolução, timing ou física.

PNG máximo 2048x2048 pixels, até 2.4 megapixels. JPEG não é suportado. Para trocar a arte, sobrescreva background.png por um PNG de mesma categoria.

O ZIP disponibilizado nesta conversa contém background.png e executáveis. O artefato bruto do GitHub Actions não inclui o PNG gerado na conversa; nesse caso, copie background.png separadamente. Nunca substitua smw_assets.dat para instalar apenas a decoração.

O ajuste de rotas de Vanilla Dome 1 permanece idêntico à versão v4 previamente testada. A branch main permanece sem mudanças.