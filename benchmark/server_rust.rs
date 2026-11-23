// benchmark/server_rust.rs — HTTP benchmark server in Rust
use std::env;
use std::io::{Read, Write};
use std::net::{TcpListener, TcpStream};
use std::thread;

fn handle_client(mut stream: TcpStream) {
    let mut buffer = [0u8; 1024];
    let n = match stream.read(&mut buffer) {
        Ok(n) if n > 0 => n,
        _ => return,
    };
    let req = String::from_utf8_lossy(&buffer[..n]);
    let path = if let Some(line) = req.lines().next() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() > 1 { parts[1] } else { "/" }
    } else {
        "/"
    };

    let (status, content_type, body) = if path == "/plaintext" {
        ("200 OK", "text/plain; charset=utf-8", "Hello, World!")
    } else if path == "/json" {
        ("200 OK", "application/json; charset=utf-8", "{\"message\":\"Hello, World!\",\"status\":\"ok\"}")
    } else {
        ("404 Not Found", "text/plain; charset=utf-8", "Not Found")
    };

    let response = format!(
        "HTTP/1.1 {}\r\nContent-Type: {}\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        status, content_type, body.len(), body
    );
    let _ = stream.write_all(response.as_bytes());
}

fn main() {
    let port = env::args().nth(1)
        .or_else(|| env::var("PORT").ok())
        .unwrap_or_else(|| "8080".to_string());
    let addr = format!("127.0.0.1:{}", port);
    let listener = TcpListener::bind(&addr).expect("Failed to bind TCP listener");
    println!("[Rust] Server listening on http://{}", addr);

    for stream in listener.incoming() {
        if let Ok(stream) = stream {
            thread::spawn(|| handle_client(stream));
        }
    }
}
