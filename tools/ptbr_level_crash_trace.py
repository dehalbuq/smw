#!/usr/bin/env python3
"""Inject PTBR level-load tracing after the R36S overlay scripts.

Purely diagnostic: no writes to SMW state, map data, or asset bytes.
Only report stage entrances, resource pointers, sprite header and loader end.
"""
import sys
from pathlib import Path

if len(sys.argv) != 2:
    sys.exit("usage: ptbr_level_crash_trace.py SMW_ROOT")
root=Path(sys.argv[1])
f=root/"src/smw_05.c"
s=f.read_text(encoding="utf-8")

def change(old,new,which):
    global s
    count=s.count(old)
    if count!=1:
        raise RuntimeError(f"{which}: expected one insertion anchor, found {count}")
    s=s.replace(old,new,1)

change("  R36SVD1_OnLoadStart();",
"""  R36SVD1_OnLoadStart();
  {
    char b[192];
    snprintf(b, sizeof(b),
             "map=%02x sublevels=%u secondary=%u bonus=%u mario=(%u,%u) "
             "layout=%02x exit_flags=%02x",
             (unsigned)ow_level_number_lo,
             (unsigned)counter_sublevels_entered,
             (unsigned)flag_use_secondary_entrance,
             (unsigned)flag_active_bonus_game,
             (unsigned)player_xpos,(unsigned)player_ypos,
             (unsigned)misc_level_layout_flags,
             (unsigned)misc_level_header_entrance_settings);
    R36SDiag_Message("PTBR_LEVEL_LOAD_BEGIN",b);
  }""", "level-begin")
change("""  ptr_layer1_data = kLevelData_Layer1(r14w).ptr;
  ptr_layer2_data = kLevelData_Layer2(r14w).ptr;""",
"""  ptr_layer1_data = kLevelData_Layer1(r14w).ptr;
  ptr_layer2_data = kLevelData_Layer2(r14w).ptr;
  {
    char b[192];
    snprintf(b,sizeof(b),"asset=%03x layer1=%p layer2=%p", 
             (unsigned)r14w,(void*)ptr_layer1_data,(void*)ptr_layer2_data);
    R36SDiag_Message("PTBR_LEVEL_DATA",b);
  }""","level-data")
change("""  uint8 sprite_hdr = *GetSpriteListPtr();""",
"""  const uint8 *spt=GetSpriteListPtr();
  {
    char b[160];
    snprintf(b,sizeof(b),"asset=%03x sprite_header_ptr=%p",
             (unsigned)r14w,(const void*)spt);
    R36SDiag_Message("PTBR_SPRITE_HEADER",b);
  }
  uint8 sprite_hdr = *spt;""","sprite-header")
change("""  R36SVD1_AfterLoad(r14w);
  return false;""",
"""  R36SVD1_AfterLoad(r14w);
  {
    char b[160];
    snprintf(b,sizeof(b),"asset=%03x mode=%02x sublevels=%u mario=(%u,%u)",
             (unsigned)r14w,(unsigned)misc_game_mode,
             (unsigned)counter_sublevels_entered,
             (unsigned)player_xpos,(unsigned)player_ypos);
    R36SDiag_Message("PTBR_LEVEL_LOAD_DONE",b);
  }
  return false;""","level-done")
f.write_text(s,encoding="utf-8",newline="\n")
print("Patched level-load tracing (no gameplay-state writes).")
