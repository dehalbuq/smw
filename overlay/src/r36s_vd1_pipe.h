#ifndef R36S_VD1_PIPE_H
#define R36S_VD1_PIPE_H
#include "types.h"
/* Narrowly scoped, reversible recovery for the 1EF -> 100 pipe seen
 * in Vanilla Dome 1 on the R36S. No impact on normal 100-star bonuses. */
void R36SVD1_OnLoadStart(void);
void R36SVD1_OnResolveLevel(uint16 *asset);
void R36SVD1_AfterLoad(uint16 asset);
void R36SVD1_OnLoaded(uint16 asset);
#endif
