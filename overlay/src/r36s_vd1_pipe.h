#ifndef R36S_VD1_PIPE_H
#define R36S_VD1_PIPE_H
#include "types.h"
/* Experimental 1EF->100 Vanilla Dome 1 pipe recovery. First seek a valid
 * original secondary entrance; otherwise restart at the stock 11A entrance.
 * Never fabricate Mario spawn coordinates. Disable with the launcher flag. */
void R36SVD1_OnLoadStart(void);
/* Before the stock secondary-entrance table lookup, replace only the
   invalid Vanilla Dome 1 exit index with an unambiguous original-ROM
   secondary entry leading back to level 11A. */
void R36SVD1_FixSecondaryEntrance(uint16 *entry, uint8 exit_screen);
void R36SVD1_OnResolveLevel(uint16 *asset);
void R36SVD1_AfterLoad(uint16 asset);
void R36SVD1_OnLoaded(uint16 asset);
#endif
