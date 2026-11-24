/* Snapshot clock for the harness process (amendment 2026-11-24 e, owner: "freeze tại ngày snapshot mcp").
 *
 * LD_PRELOAD into the harness's main process only. On load the wall clock is shifted so that it reads
 * CLOCKSHIFT_TARGET_EPOCH (seconds) at that instant and then advances normally; monotonic clocks are untouched
 * (timeouts keep working). The constructor removes LD_PRELOAD and CLOCKSHIFT_* from the environment, so child
 * processes (MCP snapshot server, shell sandbox) keep the real clock and their receipts stay auditable.
 */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdlib.h>
#include <sys/time.h>
#include <time.h>

static long long shift_ns = 0;
static int (*real_clock_gettime)(clockid_t, struct timespec *) = 0;

__attribute__((constructor)) static void clockshift_init(void) {
    real_clock_gettime = (int (*)(clockid_t, struct timespec *))dlsym(RTLD_NEXT, "clock_gettime");
    const char *target = getenv("CLOCKSHIFT_TARGET_EPOCH");
    if (target && real_clock_gettime) {
        struct timespec now;
        real_clock_gettime(CLOCK_REALTIME, &now);
        shift_ns = (atoll(target) - (long long)now.tv_sec) * 1000000000LL - now.tv_nsec;
    }
    unsetenv("LD_PRELOAD");
    unsetenv("CLOCKSHIFT_TARGET_EPOCH");
}

static void add_shift(struct timespec *ts) {
    long long ns = (long long)ts->tv_sec * 1000000000LL + ts->tv_nsec + shift_ns;
    ts->tv_sec = ns / 1000000000LL;
    ts->tv_nsec = ns % 1000000000LL;
}

int clock_gettime(clockid_t id, struct timespec *ts) {
    if (!real_clock_gettime)
        real_clock_gettime = (int (*)(clockid_t, struct timespec *))dlsym(RTLD_NEXT, "clock_gettime");
    int rc = real_clock_gettime(id, ts);
    if (rc == 0 && shift_ns && (id == CLOCK_REALTIME || id == CLOCK_REALTIME_COARSE || id == CLOCK_TAI))
        add_shift(ts);
    return rc;
}

int gettimeofday(struct timeval *tv, void *tz) {
    struct timespec ts;
    int rc = clock_gettime(CLOCK_REALTIME, &ts);
    if (rc == 0 && tv) {
        tv->tv_sec = ts.tv_sec;
        tv->tv_usec = ts.tv_nsec / 1000;
    }
    (void)tz;
    return rc;
}

time_t time(time_t *out) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    if (out) *out = ts.tv_sec;
    return ts.tv_sec;
}

int timespec_get(struct timespec *ts, int base) {
    if (base != TIME_UTC || clock_gettime(CLOCK_REALTIME, ts) != 0) return 0;
    return base;
}
