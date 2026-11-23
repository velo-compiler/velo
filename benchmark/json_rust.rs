// benchmark/json_rust.rs — JSON parsing and aggregation benchmark in Rust (std-only)
use std::env;

#[derive(Debug, PartialEq)]
#[allow(dead_code)]
enum JVal {
    Null,
    Bool(bool),
    Num(i64),
    Str(String),
    Arr(Vec<JVal>),
    Obj(Vec<(String, JVal)>),
}

struct Parser<'a> {
    bytes: &'a [u8],
    pos: usize,
}

impl<'a> Parser<'a> {
    fn new(bytes: &'a [u8]) -> Self {
        Self { bytes, pos: 0 }
    }

    fn skip_ws(&mut self) {
        while self.pos < self.bytes.len() {
            let b = self.bytes[self.pos];
            if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' {
                self.pos += 1;
            } else {
                break;
            }
        }
    }

    fn parse_str(&mut self) -> Option<String> {
        if self.pos >= self.bytes.len() || self.bytes[self.pos] != b'"' {
            return None;
        }
        self.pos += 1;
        let start = self.pos;
        while self.pos < self.bytes.len() && self.bytes[self.pos] != b'"' {
            self.pos += 1;
        }
        let s = std::str::from_utf8(&self.bytes[start..self.pos]).ok()?.to_string();
        if self.pos < self.bytes.len() && self.bytes[self.pos] == b'"' {
            self.pos += 1;
        }
        Some(s)
    }

    fn parse_val(&mut self) -> Option<JVal> {
        self.skip_ws();
        if self.pos >= self.bytes.len() {
            return None;
        }
        let b = self.bytes[self.pos];
        if b == b'[' {
            self.pos += 1;
            let mut arr = Vec::new();
            self.skip_ws();
            if self.pos < self.bytes.len() && self.bytes[self.pos] == b']' {
                self.pos += 1;
                return Some(JVal::Arr(arr));
            }
            while self.pos < self.bytes.len() {
                let v = self.parse_val()?;
                arr.push(v);
                self.skip_ws();
                if self.pos < self.bytes.len() && self.bytes[self.pos] == b',' {
                    self.pos += 1;
                } else if self.pos < self.bytes.len() && self.bytes[self.pos] == b']' {
                    self.pos += 1;
                    break;
                } else {
                    break;
                }
            }
            Some(JVal::Arr(arr))
        } else if b == b'{' {
            self.pos += 1;
            let mut obj = Vec::new();
            self.skip_ws();
            if self.pos < self.bytes.len() && self.bytes[self.pos] == b'}' {
                self.pos += 1;
                return Some(JVal::Obj(obj));
            }
            while self.pos < self.bytes.len() {
                self.skip_ws();
                let key = self.parse_str()?;
                self.skip_ws();
                if self.pos < self.bytes.len() && self.bytes[self.pos] == b':' {
                    self.pos += 1;
                }
                let val = self.parse_val()?;
                obj.push((key, val));
                self.skip_ws();
                if self.pos < self.bytes.len() && self.bytes[self.pos] == b',' {
                    self.pos += 1;
                } else if self.pos < self.bytes.len() && self.bytes[self.pos] == b'}' {
                    self.pos += 1;
                    break;
                } else {
                    break;
                }
            }
            Some(JVal::Obj(obj))
        } else if b == b'"' {
            Some(JVal::Str(self.parse_str()?))
        } else if self.bytes[self.pos..].starts_with(b"true") {
            self.pos += 4;
            Some(JVal::Bool(true))
        } else if self.bytes[self.pos..].starts_with(b"false") {
            self.pos += 5;
            Some(JVal::Bool(false))
        } else if b == b'-' || b.is_ascii_digit() {
            let start = self.pos;
            if b == b'-' { self.pos += 1; }
            while self.pos < self.bytes.len() && self.bytes[self.pos].is_ascii_digit() {
                self.pos += 1;
            }
            let s = std::str::from_utf8(&self.bytes[start..self.pos]).ok()?;
            let n: i64 = s.parse().ok()?;
            Some(JVal::Num(n))
        } else {
            None
        }
    }
}

fn obj_get<'a>(obj: &'a [(String, JVal)], key: &str) -> Option<&'a JVal> {
    for (k, v) in obj {
        if k == key {
            return Some(v);
        }
    }
    None
}

fn run_json_benchmark(payload: &str, iterations: usize) {
    let mut total_active = 0;
    let mut total_age = 0;
    let mut total_score = 0;

    let bytes = payload.as_bytes();

    for _ in 0..iterations {
        let mut parser = Parser::new(bytes);
        if let Some(JVal::Arr(items)) = parser.parse_val() {
            for item in items {
                if let JVal::Obj(members) = item {
                    if let Some(JVal::Bool(true)) = obj_get(&members, "active") {
                        total_active += 1;
                        if let Some(JVal::Num(age)) = obj_get(&members, "age") {
                            total_age += *age as i32;
                        }
                        if let Some(JVal::Arr(scores)) = obj_get(&members, "scores") {
                            if let Some(JVal::Num(s0)) = scores.first() {
                                total_score += *s0 as i32;
                            }
                        }
                    }
                }
            }
        }
    }

    println!("Done {} iterations: active={}, age={}, score={}", iterations, total_active, total_age, total_score);
}

fn main() {
    let payload = "[{\"id\":1,\"name\":\"Alice\",\"age\":28,\"active\":true,\"scores\":[85,92,78]},{\"id\":2,\"name\":\"Bob\",\"age\":34,\"active\":false,\"scores\":[70,75,80]},{\"id\":3,\"name\":\"Charlie\",\"age\":22,\"active\":true,\"scores\":[95,98,91]},{\"id\":4,\"name\":\"Diana\",\"age\":41,\"active\":true,\"scores\":[88,84,90]},{\"id\":5,\"name\":\"Evan\",\"age\":29,\"active\":false,\"scores\":[65,72,68]},{\"id\":6,\"name\":\"Fiona\",\"age\":31,\"active\":true,\"scores\":[92,89,94]},{\"id\":7,\"name\":\"George\",\"age\":50,\"active\":true,\"scores\":[79,83,85]},{\"id\":8,\"name\":\"Hannah\",\"age\":26,\"active\":false,\"scores\":[81,77,86]},{\"id\":9,\"name\":\"Ian\",\"age\":38,\"active\":true,\"scores\":[87,91,89]},{\"id\":10,\"name\":\"Julia\",\"age\":24,\"active\":true,\"scores\":[96,94,99]}]";
    let args: Vec<String> = env::args().collect();
    let iters: usize = if args.len() > 1 {
        args[1].parse().unwrap_or(5000)
    } else {
        5000
    };
    run_json_benchmark(payload, iters);
}
