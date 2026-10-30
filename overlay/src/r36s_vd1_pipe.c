#include "r36s_vd1_pipe.h"
#include "smw_rtl.h"
#include "variables.h"
#include "r36s_diag.h"
#include <stdio.h>
#include <stdlib.h>

static uint16 s_previous_asset = 0xffff;
static uint16 s_pipe_x,s_pipe_y,s_cam1x,s_cam1y,s_cam2x,s_cam2y;
static uint8 s_origin_screen,s_invalid_exit_screen;
static int s_pipe_snapshot_valid,s_recovery_pending;

/* Called before LoadLevel alters player/camera coordinates. */
void R36SVD1_OnLoadStart(void) {
  if (ow_level_number_lo == 0x3e && counter_sublevels_entered == 1 &&
      s_previous_asset == 0x11a) {
    s_pipe_x = player_xpos;
    s_pipe_y = player_ypos;
    s_cam1x = mirror_current_layer1_xpos;
    s_cam1y = mirror_current_layer1_ypos;
    s_cam2x = mirror_current_layer2_xpos;
    s_cam2y = mirror_current_layer2_ypos;
    s_origin_screen = (misc_level_layout_flags & 1) ? (uint8)(player_ypos >> 8)
                                                     : (uint8)(player_xpos >> 8);
    s_pipe_snapshot_valid = 1;
  }
  if (ow_level_number_lo == 0x3e && counter_sublevels_entered == 2 &&
      s_previous_asset == 0x1ef) {
    s_invalid_exit_screen=(misc_level_layout_flags & 1) ?
        (uint8)(player_ypos >> 8) : (uint8)(player_xpos >> 8);
  }
}

/* The documented Vanilla Dome 1 main and second areas are 11A/1EF.
 * The log proves a pipe in 1EF is incorrectly resolving to bonus 100
 * with bonus flag=0. Only repair this precise sequence when we have
 * the player's known previous main-level pipe position to return to.
 *
 * This is a temporary, testable recovery rather than an assertion
 * about the missing source ROM's exit metadata. */
void R36SVD1_OnResolveLevel(uint16 *asset) {
  if (!asset || ow_level_number_lo != 0x3e ||
      s_previous_asset != 0x1ef || counter_sublevels_entered != 2 ||
      *asset != 0x100 || flag_active_bonus_game != 0)
    return;
  int screen = s_invalid_exit_screen;
  int prev = screen ? screen-1 : screen;
  int next = screen < 31 ? screen+1 : screen;
  char message[330];
  snprintf(message,sizeof(message),
           "Vanilla Dome 1 invalid pipe: source=1ef dest=100 screen=%d "
           "exit[prev=%d]=%02x exit[cur=%d]=%02x exit[next=%d]=%02x "
           "props[cur]=%02x snapshot_valid=%d orig_screen=%u",
           screen,prev,misc_subscreen_exit_entrance_number_lo[prev & 31],
           screen,misc_subscreen_exit_entrance_number_lo[screen & 31],
           next,misc_subscreen_exit_entrance_number_lo[next & 31],
           misc_subscreen_exit_properties[screen & 31],s_pipe_snapshot_valid,s_origin_screen);
  R36SDiag_Message("VD1_INVALID_EXIT",message);

  const char *opt=getenv("SMW_R36S_VD1_PIPE_FIX");
  if (!s_pipe_snapshot_valid || (opt && opt[0]=='0')) {
    R36SDiag_Message("VD1_PIPE_RECOVERY","disabled or missing main-pipe snapshot");
    return;
  }
  /* Restore a known playable location of the parent level, just past
   * the original pipe. Users can opt out with SMW_R36S_VD1_PIPE_FIX=0. */
  *asset=0x11a;
  flag_use_secondary_entrance=0;
  s_recovery_pending=1;
  R36SDiag_Message("VD1_PIPE_RECOVERY",
                   "experimental: rerouting 1EF->100 to 11A at prior pipe+64px");
}

void R36SVD1_AfterLoad(uint16 asset) {
  if (!s_recovery_pending)
    return;
  s_recovery_pending=0;
  if (asset!=0x11a) {
    R36SDiag_Message("VD1_PIPE_RECOVERY","aborted, unexpected destination");
    return;
  }
  /* Return to the original map area rather than keeping bonus 100's
   * initialization (Mario=(16,0), camera=(0,0)). Spawn slightly above
   * the saved floor to avoid starting embedded in a solid tile. */
  player_xpos=(uint16)(s_pipe_x + 64);
  player_ypos=(uint16)(s_pipe_y - 16);
  mirror_current_layer1_xpos=(uint16)(s_cam1x + 64);
  mirror_current_layer1_ypos=s_cam1y;
  mirror_current_layer2_xpos=(uint16)(s_cam2x + 64);
  mirror_current_layer2_ypos=s_cam2y;
  misc_level_header_entrance_settings=0;
  char message[160];
  snprintf(message,sizeof(message),
           "redirected to 11a player=(%u,%u) camera=(%u,%u), source=(%u,%u)",
           (unsigned)player_xpos,(unsigned)player_ypos,
           (unsigned)mirror_current_layer1_xpos,(unsigned)mirror_current_layer1_ypos,
           (unsigned)s_pipe_x,(unsigned)s_pipe_y);
  R36SDiag_Message("VD1_PIPE_RECOVERY",message);
}

void R36SVD1_OnLoaded(uint16 asset) {
  s_previous_asset=asset;
  if (ow_level_number_lo!=0x3e)
    s_pipe_snapshot_valid=0;
}
