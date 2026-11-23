// benchmark/json_c.c — JSON parsing and aggregation benchmark in C
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdbool.h>
#include <ctype.h>

typedef enum {
    J_NULL, J_BOOL, J_NUM, J_STR, J_ARRAY, J_OBJ
} JType;

typedef struct JVal JVal;

typedef struct {
    char* key;
    JVal* val;
} JMember;

struct JVal {
    JType type;
    union {
        bool b;
        long num;
        char* str;
        struct { JVal** items; size_t count; } arr;
        struct { JMember* members; size_t count; } obj;
    } u;
};

static void skip_ws(const char** p) {
    while (**p && (**p == ' ' || **p == '\t' || **p == '\n' || **p == '\r')) (*p)++;
}

static JVal* parse_val(const char** p);

static char* parse_str_raw(const char** p) {
    if (**p != '"') return NULL;
    (*p)++;
    const char* start = *p;
    while (**p && **p != '"') (*p)++;
    size_t len = *p - start;
    char* res = (char*)malloc(len + 1);
    memcpy(res, start, len);
    res[len] = '\0';
    if (**p == '"') (*p)++;
    return res;
}

static JVal* parse_array(const char** p) {
    (*p)++; // skip '['
    JVal* v = (JVal*)calloc(1, sizeof(JVal));
    v->type = J_ARRAY;
    size_t cap = 8;
    v->u.arr.items = (JVal**)malloc(cap * sizeof(JVal*));
    v->u.arr.count = 0;

    skip_ws(p);
    if (**p == ']') { (*p)++; return v; }

    while (**p) {
        skip_ws(p);
        JVal* item = parse_val(p);
        if (v->u.arr.count >= cap) {
            cap *= 2;
            v->u.arr.items = (JVal**)realloc(v->u.arr.items, cap * sizeof(JVal*));
        }
        v->u.arr.items[v->u.arr.count++] = item;
        skip_ws(p);
        if (**p == ',') { (*p)++; }
        else if (**p == ']') { (*p)++; break; }
        else break;
    }
    return v;
}

static JVal* parse_obj(const char** p) {
    (*p)++; // skip '{'
    JVal* v = (JVal*)calloc(1, sizeof(JVal));
    v->type = J_OBJ;
    size_t cap = 8;
    v->u.obj.members = (JMember*)malloc(cap * sizeof(JMember));
    v->u.obj.count = 0;

    skip_ws(p);
    if (**p == '}') { (*p)++; return v; }

    while (**p) {
        skip_ws(p);
        char* key = parse_str_raw(p);
        skip_ws(p);
        if (**p == ':') (*p)++;
        skip_ws(p);
        JVal* val = parse_val(p);

        if (v->u.obj.count >= cap) {
            cap *= 2;
            v->u.obj.members = (JMember*)realloc(v->u.obj.members, cap * sizeof(JMember));
        }
        v->u.obj.members[v->u.obj.count].key = key;
        v->u.obj.members[v->u.obj.count].val = val;
        v->u.obj.count++;

        skip_ws(p);
        if (**p == ',') { (*p)++; }
        else if (**p == '}') { (*p)++; break; }
        else break;
    }
    return v;
}

static JVal* parse_val(const char** p) {
    skip_ws(p);
    if (!**p) return NULL;
    if (**p == '[') return parse_array(p);
    if (**p == '{') return parse_obj(p);
    if (**p == '"') {
        JVal* v = (JVal*)calloc(1, sizeof(JVal));
        v->type = J_STR;
        v->u.str = parse_str_raw(p);
        return v;
    }
    if (strncmp(*p, "true", 4) == 0) {
        JVal* v = (JVal*)calloc(1, sizeof(JVal));
        v->type = J_BOOL;
        v->u.b = true;
        *p += 4;
        return v;
    }
    if (strncmp(*p, "false", 5) == 0) {
        JVal* v = (JVal*)calloc(1, sizeof(JVal));
        v->type = J_BOOL;
        v->u.b = false;
        *p += 5;
        return v;
    }
    if (**p == '-' || isdigit((unsigned char)**p)) {
        char* end = NULL;
        long n = strtol(*p, &end, 10);
        *p = end;
        JVal* v = (JVal*)calloc(1, sizeof(JVal));
        v->type = J_NUM;
        v->u.num = n;
        return v;
    }
    return NULL;
}

static void free_val(JVal* v) {
    if (!v) return;
    if (v->type == J_STR) {
        free(v->u.str);
    } else if (v->type == J_ARRAY) {
        for (size_t i = 0; i < v->u.arr.count; i++) free_val(v->u.arr.items[i]);
        free(v->u.arr.items);
    } else if (v->type == J_OBJ) {
        for (size_t i = 0; i < v->u.obj.count; i++) {
            free(v->u.obj.members[i].key);
            free_val(v->u.obj.members[i].val);
        }
        free(v->u.obj.members);
    }
    free(v);
}

static JVal* obj_get(JVal* obj, const char* key) {
    if (!obj || obj->type != J_OBJ) return NULL;
    for (size_t i = 0; i < obj->u.obj.count; i++) {
        if (strcmp(obj->u.obj.members[i].key, key) == 0) return obj->u.obj.members[i].val;
    }
    return NULL;
}

int main(int argc, char** argv) {
    const char* payload = "[{\"id\":1,\"name\":\"Alice\",\"age\":28,\"active\":true,\"scores\":[85,92,78]},{\"id\":2,\"name\":\"Bob\",\"age\":34,\"active\":false,\"scores\":[70,75,80]},{\"id\":3,\"name\":\"Charlie\",\"age\":22,\"active\":true,\"scores\":[95,98,91]},{\"id\":4,\"name\":\"Diana\",\"age\":41,\"active\":true,\"scores\":[88,84,90]},{\"id\":5,\"name\":\"Evan\",\"age\":29,\"active\":false,\"scores\":[65,72,68]},{\"id\":6,\"name\":\"Fiona\",\"age\":31,\"active\":true,\"scores\":[92,89,94]},{\"id\":7,\"name\":\"George\",\"age\":50,\"active\":true,\"scores\":[79,83,85]},{\"id\":8,\"name\":\"Hannah\",\"age\":26,\"active\":false,\"scores\":[81,77,86]},{\"id\":9,\"name\":\"Ian\",\"age\":38,\"active\":true,\"scores\":[87,91,89]},{\"id\":10,\"name\":\"Julia\",\"age\":24,\"active\":true,\"scores\":[96,94,99]}]";
    int iterations = 5000;
    if (argc > 1 && argv[1]) {
        iterations = atoi(argv[1]);
        if (iterations <= 0) iterations = 5000;
    }

    int total_active = 0;
    int total_age = 0;
    int total_score = 0;

    for (int it = 0; it < iterations; it++) {
        const char* p = payload;
        JVal* root = parse_val(&p);
        if (root && root->type == J_ARRAY) {
            for (size_t i = 0; i < root->u.arr.count; i++) {
                JVal* item = root->u.arr.items[i];
                if (item && item->type == J_OBJ) {
                    JVal* v_active = obj_get(item, "active");
                    if (v_active && v_active->type == J_BOOL && v_active->u.b) {
                        total_active++;
                        JVal* v_age = obj_get(item, "age");
                        if (v_age && v_age->type == J_NUM) total_age += (int)v_age->u.num;
                        JVal* v_scores = obj_get(item, "scores");
                        if (v_scores && v_scores->type == J_ARRAY && v_scores->u.arr.count > 0) {
                            JVal* s0 = v_scores->u.arr.items[0];
                            if (s0 && s0->type == J_NUM) total_score += (int)s0->u.num;
                        }
                    }
                }
            }
        }
        free_val(root);
    }

    printf("Done %d iterations: active=%d, age=%d, score=%d\n", iterations, total_active, total_age, total_score);
    return 0;
}
