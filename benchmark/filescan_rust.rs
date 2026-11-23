// benchmark/filescan_rust.rs — File scanning & word count benchmark in Rust
use std::env;
use std::fs;

fn scan_file(path: &str) -> Result<(), Box<dyn std::error::Error>> {
    let bytes = fs::read(path)?;
    let len = bytes.len();
    let mut lines: usize = 0;
    let mut words: usize = 0;
    let mut in_word = false;

    for &b in &bytes {
        if b == b'\n' {
            lines += 1;
        }
        if b == b' ' || b == b'\t' || b == b'\n' || b == b'\r' {
            in_word = false;
        } else if !in_word {
            in_word = true;
            words += 1;
        }
    }

    println!("Scanned: lines={}, words={}, bytes={}", lines, words, len);
    Ok(())
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let target = if args.len() > 1 && !args[1].is_empty() {
        &args[1]
    } else {
        "bootstrap.c"
    };

    if let Err(e) = scan_file(target) {
        eprintln!("[Rust Error] {}", e);
        std::process::exit(1);
    }
}
