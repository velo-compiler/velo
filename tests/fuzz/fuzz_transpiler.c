/* tests/fuzz/fuzz_transpiler.c
 *
 * LibFuzzer / AFL entry point for the Velo C-transpiler path.
 *
 * Exposes LLVMFuzzerTestOneInput and LLVMFuzzerInitialize for libFuzzer and AFL++,
 * and provides a standalone test runner when compiled without a fuzzing engine.
 *
 * Phase 82 / Task 82.3 (Invariant I82.3)
 */

#include <stdint.h>
#include <stddef.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <io.h>
#include <process.h>
#include <direct.h>
#define getpid _getpid
#else
#include <unistd.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <dirent.h>
#endif

#include "velo_runtime.h"

/* Velo compiler declarations exported by bootstrap.c */
extern const char* compile_source_to_c_all_opts(
    const char* source_path,
    bool unsafe_index,
    bool is_test,
    bool no_line_directives,
    bool strict_safety
);

extern void diag_collector_start(void);
extern void diag_collector_clear(void);
extern void diag_collector_stop(void);
extern void velo_heap_free(void* ptr);

static char s_scratch_file[1024] = {0};
static bool s_initialized = false;
static bool s_silent = false;

static void silence_stdout(void) {
#ifdef _WIN32
    freopen("NUL", "w", stdout);
#else
    freopen("/dev/null", "w", stdout);
#endif
}

static void init_scratch_file(void) {
    if (s_scratch_file[0] != '\0') return;

#ifdef _WIN32
    const char *tmp = getenv("TEMP");
    if (!tmp) tmp = getenv("TMP");
    if (!tmp) tmp = ".velo_cache";
    snprintf(s_scratch_file, sizeof(s_scratch_file), "%s/velo_fuzz_%d.vl",
             tmp, (int)getpid());
#else
    /* On Linux, check /dev/shm for zero-I/O ramfs */
    if (access("/dev/shm", W_OK) == 0) {
        snprintf(s_scratch_file, sizeof(s_scratch_file), "/dev/shm/.velo_fuzz_%d.vl", (int)getpid());
    } else {
        const char *tmp = getenv("TMPDIR");
        if (!tmp) tmp = "/tmp";
        snprintf(s_scratch_file, sizeof(s_scratch_file), "%s/.velo_fuzz_%d.vl", tmp, (int)getpid());
    }
#endif
}

static void cleanup_scratch_file(void) {
    if (s_scratch_file[0] != '\0') {
        remove(s_scratch_file);
        s_scratch_file[0] = '\0';
    }
}

#if defined(__cplusplus)
extern "C" {
#endif

int LLVMFuzzerInitialize(int *argc, char ***argv) {
    (void)argc;
    (void)argv;
    init_scratch_file();
    atexit(cleanup_scratch_file);
    diag_collector_start();
    s_initialized = true;
    return 0;
}

int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size) {
    if (!s_initialized) {
        init_scratch_file();
        atexit(cleanup_scratch_file);
        diag_collector_start();
        s_initialized = true;
    }

    /* Reject 0-length and oversized inputs (> 256 KB) */
    if (size == 0 || size > 262144) {
        return 0;
    }

    FILE *f = fopen(s_scratch_file, "wb");
    if (!f) return 0;
    size_t written = fwrite(data, 1, size, f);
    fclose(f);
    if (written != size) return 0;

    /* Push zone watermark to reclaim all compiler AST, symbol, and string memory */
    size_t zone_mark = velo_zone_push();
    diag_collector_clear();

    /* Transpile source to C */
    const char *c_code = compile_source_to_c_all_opts(
        s_scratch_file,
        false, /* unsafe_index */
        false, /* is_test */
        false, /* no_line_directives */
        false  /* strict_safety */
    );
    (void)c_code;

    /* Reset diagnostics and pop compiler zone memory in O(1) */
    diag_collector_clear();
    velo_zone_pop(zone_mark);

    return 0;
}

#if defined(__cplusplus)
}
#endif

/* Standalone test driver when compiled without libFuzzer/AFL */
#if !defined(FUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION) && !defined(__AFL_COMPILER) && !defined(NO_STANDALONE_MAIN)

static int test_single_file(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        fprintf(stderr, "[fuzz] Cannot open file: %s\n", path);
        return 1;
    }
    fseek(f, 0, SEEK_END);
    long sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz < 0 || sz > 10 * 1024 * 1024) {
        fclose(f);
        return 0;
    }

    uint8_t *buf = (uint8_t*)malloc((size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return 1;
    }
    size_t rd = fread(buf, 1, (size_t)sz, f);
    fclose(f);

    int rc = LLVMFuzzerTestOneInput(buf, rd);
    free(buf);
    return rc;
}

static void mutate_buffer(uint8_t *buf, size_t *size, size_t max_cap) {
    if (*size == 0) return;
    int op = rand() % 5;
    size_t idx = (size_t)(rand() % (int)(*size));
    switch (op) {
        case 0: /* Bit flip */
            buf[idx] ^= (uint8_t)(1 << (rand() % 8));
            break;
        case 1: /* Byte replacement */
            buf[idx] = (uint8_t)(rand() % 256);
            break;
        case 2: /* Insert byte */
            if (*size + 1 < max_cap) {
                memmove(buf + idx + 1, buf + idx, *size - idx);
                buf[idx] = (uint8_t)(rand() % 256);
                (*size)++;
            }
            break;
        case 3: /* Delete byte */
            if (*size > 1) {
                memmove(buf + idx, buf + idx + 1, *size - idx - 1);
                (*size)--;
            }
            break;
        case 4: /* Swap adjacent */
            if (idx + 1 < *size) {
                uint8_t tmp = buf[idx];
                buf[idx] = buf[idx + 1];
                buf[idx + 1] = tmp;
            }
            break;
    }
}

static int run_standalone_budget(int budget_seconds, const char *seed_file) {
    fprintf(stderr, "[fuzz] Running standalone mutation fuzzer for %d seconds (seed: %s)...\n",
            budget_seconds, seed_file ? seed_file : "default");

    uint8_t seed[8192];
    size_t seed_len = 0;

    if (seed_file) {
        FILE *f = fopen(seed_file, "rb");
        if (f) {
            seed_len = fread(seed, 1, sizeof(seed) - 1, f);
            fclose(f);
        }
    }
    if (seed_len == 0) {
        const char *fallback = "act main() -> i32 { return 0 }\n";
        seed_len = strlen(fallback);
        memcpy(seed, fallback, seed_len);
    }

    uint8_t mut_buf[16384];
    time_t start = time(NULL);
    long iterations = 0;

    srand((unsigned int)start);

    while (time(NULL) - start < budget_seconds) {
        memcpy(mut_buf, seed, seed_len);
        size_t cur_len = seed_len;
        int num_mut = 1 + (rand() % 4);
        for (int m = 0; m < num_mut; m++) {
            mutate_buffer(mut_buf, &cur_len, sizeof(mut_buf));
        }

        LLVMFuzzerTestOneInput(mut_buf, cur_len);
        iterations++;
    }

    fprintf(stderr, "[fuzz] Completed %ld iterations in %d seconds with 0 crashes.\n",
            iterations, budget_seconds);
    return 0;
}

int main(int argc, char **argv) {
    if (argc > 1 && (strcmp(argv[1], "--help") == 0 || strcmp(argv[1], "-h") == 0)) {
        printf("Usage: %s [OPTIONS] [FILE...]\n", argv[0]);
        printf("Options:\n");
        printf("  --budget <SEC> [SEED_FILE]  Run standalone mutation fuzzing for SEC seconds\n");
        printf("  --silent                    Suppress diagnostic logging\n");
        printf("  --help, -h                  Show this help\n");
        return 0;
    }

    int budget = 0;
    const char *seed_file = NULL;
    int file_start = 1;

    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "--silent") == 0) {
            s_silent = true;
            silence_stdout();
            file_start = i + 1;
        } else if (strcmp(argv[i], "--budget") == 0 && i + 1 < argc) {
            budget = atoi(argv[i + 1]);
            if (i + 2 < argc && argv[i + 2][0] != '-') {
                seed_file = argv[i + 2];
                i++;
            }
            i++;
            file_start = i + 1;
        }
    }

    if (budget > 0) {
        return run_standalone_budget(budget, seed_file);
    }

    if (file_start >= argc) {
        /* Default: run a minimal smoke test */
        const char *smoke = "act main() -> i32 { return 42 }\n";
        return LLVMFuzzerTestOneInput((const uint8_t*)smoke, strlen(smoke));
    }

    int errors = 0;
    for (int i = file_start; i < argc; i++) {
        int rc = test_single_file(argv[i]);
        if (rc != 0) {
            fprintf(stderr, "[fuzz] Failure on file: %s\n", argv[i]);
            errors++;
        }
    }

    return errors == 0 ? 0 : 1;
}

#endif
