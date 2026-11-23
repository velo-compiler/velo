// benchmark/filescan_c.c — File scanning & word count benchmark in C
#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>

static int scan_file(const char* path) {
    FILE* fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "[C Error] Failed to open file: %s\n", path);
        return 1;
    }

    fseek(fp, 0, SEEK_END);
    long len = ftell(fp);
    fseek(fp, 0, SEEK_SET);

    char* buffer = (char*)malloc(len + 1);
    if (!buffer) {
        fclose(fp);
        return 1;
    }

    size_t read_bytes = fread(buffer, 1, len, fp);
    fclose(fp);
    buffer[read_bytes] = '\0';

    size_t lines = 0;
    size_t words = 0;
    bool in_word = false;

    for (size_t i = 0; i < read_bytes; i++) {
        char ch = buffer[i];
        if (ch == '\n') {
            lines++;
        }
        if (ch == ' ' || ch == '\t' || ch == '\n' || ch == '\r') {
            in_word = false;
        } else if (!in_word) {
            in_word = true;
            words++;
        }
    }

    free(buffer);
    printf("Scanned: lines=%zu, words=%zu, bytes=%zu\n", lines, words, read_bytes);
    return 0;
}

int main(int argc, char** argv) {
    const char* target = "bootstrap.c";
    if (argc > 1 && argv[1] && argv[1][0] != '\0') {
        target = argv[1];
    }
    return scan_file(target);
}
