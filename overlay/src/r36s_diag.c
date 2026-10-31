#define _GNU_SOURCE
#define _POSIX_C_SOURCE 200809L
#include "r36s_diag.h"
#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>
#if defined(__linux__)
#include <ucontext.h>
#endif

/* SNES RAM offsets correspond to src/variables.h. */
extern uint8_t g_ram[0x20000];
static int log_fd = -1;
static volatile sig_atomic_t diag_frame, diag_phase, diag_inputs, in_signal;
static uint8_t last_game_id = 255, last_mode = 255, last_level = 255, last_exit = 255;
static int last_had_mismatch;
/* Bonus rooms and pipe transitions do not necessarily change the overworld
 * level id ($13BF). Track sublevel count and sprite 0x82 explicitly. */
static uint8_t last_sublevels=255, last_bonus_flag=255;

static void append_str(char *out, size_t *pos, size_t cap, const char *s) {
  while (*s && *pos + 1 < cap) out[(*pos)++] = *s++;
}
static void append_hex(char *out, size_t *pos, size_t cap, uintptr_t n) {
  static const char digits[] = "0123456789abcdef";
  append_str(out, pos, cap, "0x");
  int shift = (int)(sizeof(uintptr_t) * 8 - 4), started = 0;
  for (; shift >= 0; shift -= 4) {
    unsigned v = (unsigned)((n >> shift) & 15);
    if (v || started || shift == 0) {
      started = 1;
      if (*pos + 1 < cap) out[(*pos)++] = digits[v];
    }
  }
}
static void append_dec(char *out, size_t *pos, size_t cap, unsigned v) {
  char tmp[16]; int n = 0;
  do { tmp[n++] = '0' + v % 10; v /= 10; } while (v && n < (int)sizeof(tmp));
  while (n && *pos + 1 < cap) out[(*pos)++] = tmp[--n];
}
static void crash_handler(int sig, siginfo_t *info, void *context) {
#if !(defined(__aarch64__) && defined(__linux__))
  (void)context;
#endif
  if (in_signal) _exit(128 + sig);
  in_signal = 1;
  char buffer[512]; size_t p = 0;
  append_str(buffer, &p, sizeof(buffer), "\n[FATAL_SIGNAL] signal=");
  append_dec(buffer, &p, sizeof(buffer), (unsigned)sig);
  append_str(buffer, &p, sizeof(buffer), " frame=");
  append_dec(buffer, &p, sizeof(buffer), (unsigned)diag_frame);
  append_str(buffer, &p, sizeof(buffer), " phase=");
  append_dec(buffer, &p, sizeof(buffer), (unsigned)diag_phase);
  append_str(buffer, &p, sizeof(buffer), " inputs=");
  append_hex(buffer, &p, sizeof(buffer), (uint32_t)diag_inputs);
  append_str(buffer, &p, sizeof(buffer), " fault_addr=");
  append_hex(buffer, &p, sizeof(buffer), (uintptr_t)(info ? info->si_addr : 0));
#if defined(__aarch64__) && defined(__linux__)
  if (context) {
    const ucontext_t *ctx = (const ucontext_t *)context;
    append_str(buffer, &p, sizeof(buffer), " pc=");
    append_hex(buffer, &p, sizeof(buffer), (uintptr_t)ctx->uc_mcontext.pc);
    append_str(buffer, &p, sizeof(buffer), " sp=");
    append_hex(buffer, &p, sizeof(buffer), (uintptr_t)ctx->uc_mcontext.sp);
  }
#endif
  append_str(buffer, &p, sizeof(buffer), " mode=");
  append_hex(buffer, &p, sizeof(buffer), g_ram[0x100]);
  append_str(buffer, &p, sizeof(buffer), " level=");
  append_hex(buffer, &p, sizeof(buffer), g_ram[0x13bf]);
  append_str(buffer, &p, sizeof(buffer), " exit=");
  append_hex(buffer, &p, sizeof(buffer), g_ram[0xdd5]);
  if (p + 1 < sizeof(buffer)) buffer[p++] = '\n';
  if (log_fd >= 0) { (void)write(log_fd, buffer, p); (void)fsync(log_fd); }
  (void)write(STDERR_FILENO, buffer, p);
  /* Prevent unbounded core dumps on a 1 GB handheld. */
  _exit(128 + sig);
}
void R36SDiag_Message(const char *type, const char *message) {
  if (!type) type = "INFO";
  if (!message) message = "";
  char buf[1024];
  int n = snprintf(buf, sizeof(buf), "[%s] %s\n", type, message);
  if (n < 0) return;
  size_t size = (size_t)n < sizeof(buf) ? (size_t)n : sizeof(buf) - 1;
  if (log_fd >= 0) (void)write(log_fd, buf, size);
  (void)write(STDERR_FILENO, buf, size);
}
void R36SDiag_Init(void) {
  (void)mkdir("logs", 0755);
  log_fd = open("logs/r36s-diagnostic.log", O_WRONLY | O_APPEND | O_CREAT | O_CLOEXEC, 0644);
  char buf[160];
  time_t now = time(NULL);
  snprintf(buf, sizeof(buf), "session_start_epoch=%lld build=%s %s sizeof_ptr=%lu",
           (long long)now, __DATE__, __TIME__, (unsigned long)sizeof(void*));
  R36SDiag_Message("START", buf);
  struct sigaction sa; memset(&sa, 0, sizeof(sa));
  sigemptyset(&sa.sa_mask);
  sa.sa_sigaction = crash_handler;
  sa.sa_flags = SA_SIGINFO | SA_RESETHAND;
  (void)sigaction(SIGSEGV, &sa, NULL);
  (void)sigaction(SIGBUS, &sa, NULL);
  (void)sigaction(SIGABRT, &sa, NULL);
  (void)sigaction(SIGILL, &sa, NULL);
  (void)sigaction(SIGFPE, &sa, NULL);
}
void R36SDiag_Assets(size_t size, unsigned int count) {
  char b[160];
  snprintf(b, sizeof(b), "assets_validated size=%lu count=%u", (unsigned long)size, count);
  R36SDiag_Message("ASSETS", b);
}
void R36SDiag_BeforeFrame(uint32_t frame, uint32_t inputs) {
  diag_frame = (sig_atomic_t)frame;
  diag_inputs = (sig_atomic_t)inputs;
  diag_phase = 1;
}
void R36SDiag_AfterFrame(uint32_t frame, uint32_t inputs, int mismatch_count, uint8_t game_id) {
  diag_phase = 2;
  uint8_t mode = g_ram[0x100], level = g_ram[0x13bf], exit_action = g_ram[0xdd5];
  int changed = mode != last_mode || level != last_level || exit_action != last_exit || game_id != last_game_id;
  int mismatch = mismatch_count > 0;
  if (changed || frame % 120 == 0 || (mismatch && !last_had_mismatch)) {
    uint16_t x = (uint16_t)(g_ram[0x94] | g_ram[0x95] << 8);
    uint16_t y = (uint16_t)(g_ram[0x96] | g_ram[0x97] << 8);
    char b[256];
    snprintf(b, sizeof(b), "frame=%u game=%u mode=%02x level=%02x exit=%02x pos=(%u,%u) inputs=%08x mismatch=%d%s",
             frame, game_id, mode, level, exit_action, x, y, inputs, mismatch_count,
             changed ? " TRANSITION" : "");
    R36SDiag_Message(changed ? "STATE_CHANGE" : "HEARTBEAT", b);
    if (changed && log_fd >= 0) (void)fsync(log_fd);
  }
  if (mismatch && !last_had_mismatch)
    R36SDiag_Message("DIVERGENCE", "Emulation/port mismatch detected; inspect saves/*-bug-*.sav");
  /* Additional diagnostics run only on transitions and once per 120 frames
   * in sublevels. No game-state writes or gameplay changes. */
  uint8_t sublevels = g_ram[0x141a];
  uint8_t bonus = g_ram[0x1425];
  if (sublevels != last_sublevels || bonus != last_bonus_flag ||
      ((frame % 120) == 0 && (sublevels || bonus))) {
    uint16_t player_y = (uint16_t)(g_ram[0x96] | g_ram[0x97] << 8);
    uint16_t camera_y = (uint16_t)(g_ram[0x1c] | g_ram[0x1d] << 8);
    uint16_t screen_y = (uint16_t)(g_ram[0x80] | g_ram[0x81] << 8);
    char msg[272];
    snprintf(msg, sizeof(msg),
             "frame=%u map=%02x sublevels=%u bonus=%u secondary=%u entrance=%u "
             "player_y=%u camera_y=%u screen_y=%u bonus_sprite_initialized=%u",
             frame, level, sublevels, bonus, g_ram[0x1b93], g_ram[0x192a],
             player_y, camera_y, screen_y, g_ram[0x1b94]);
    R36SDiag_Message("SUBLEVEL", msg);
  }
  /* 0x82 is the native 1-UP bonus roulette sprite. Inspect actual
   * coordinates, not the position of the overworld level. */
  if ((frame % 120) == 0 || changed) {
    unsigned count = 0;
    char msg[512];
    size_t used = 0;
    for (int slot = 0; slot < 12; slot++) {
      if (g_ram[0x14c8 + slot] && g_ram[0x9e + slot] == 0x82) {
        if (!count) {
          int n = snprintf(msg, sizeof(msg),
               "frame=%u level=%02x sublevels=%u bonus=%u cam_y=%u mario_y=%u sprites=",
               frame, level, sublevels, bonus,
               (unsigned)(g_ram[0x1c] | g_ram[0x1d] << 8),
               (unsigned)(g_ram[0x96] | g_ram[0x97] << 8));
          used = n > 0 ? (size_t)n : 0;
          if (used >= sizeof(msg)) used = sizeof(msg)-1;
        }
        if (used < sizeof(msg) - 52) {
          int n = snprintf(msg + used, sizeof(msg) - used,
                  "[%d x=%u y=%u] ", slot,
                  (unsigned)(g_ram[0xe4 + slot] | g_ram[0x14e0 + slot] << 8),
                  (unsigned)(g_ram[0xd8 + slot] | g_ram[0x14d4 + slot] << 8));
          if (n > 0) used += (size_t)n;
        }
        count++;
      }
    }
    if (count) R36SDiag_Message("BONUS_SPRITES", msg);
  }
  last_sublevels = sublevels;
  last_bonus_flag = bonus;
  last_game_id = game_id;
  last_mode = mode; last_level = level; last_exit = exit_action;
  last_had_mismatch = mismatch;
}
void R36SDiag_Close(void) {
  R36SDiag_Message("SHUTDOWN", "Normal exit");
  if (log_fd >= 0) { (void)fsync(log_fd); (void)close(log_fd); log_fd = -1; }
}
