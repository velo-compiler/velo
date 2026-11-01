import { StdlibModule } from '../types/docs';

export const STDLIB_MODULES: StdlibModule[] = [
  // ================= TIER 1: CORE FOUNDATION (ZERO LIBC) =================
  {
    name: 'std.mem',
    category: 'Memory & Allocators',
    tier: 1,
    description: 'Pure Velo virtual memory page allocators, lexical arena watermarking, and dynamic slab freelists. Zero reliance on libc malloc.',
    pureVelo: true,
    loc: 2450,
    functions: [
      {
        name: 'mem.alloc',
        signature: 'act mem.alloc[T](@Type, count: usize) -> @T',
        description: 'Allocates memory on the current active zone arena. Bump allocation executes in 1-2 CPU cycles.',
        example: 'points: @Point = mem.alloc(@Point, 1000)'
      },
      {
        name: 'mem.used',
        signature: 'act mem.used() -> usize',
        description: 'Returns the total number of bytes currently active on the thread zone arena buffer.',
        example: 'let bytes = mem.used()'
      },
      {
        name: 'mem.heap_alloc',
        signature: 'act mem.heap_alloc[T](@Type, count: usize) -> @T',
        description: 'Allocates persistent heap memory backed by OS virtual memory pages. Survives zone resets.',
        example: 'buf: @u8 = mem.heap_alloc(@u8, 4096)'
      },
      {
        name: 'mem.free',
        signature: 'act mem.free(ptr: @void)',
        description: 'Releases persistent heap memory back to the allocator. Idiomatically paired with defer.',
        example: 'defer mem.free(buf)'
      },
      {
        name: 'mem.copy',
        signature: 'act mem.copy(dst: @void, src: @void, byte_count: usize)',
        description: 'High-speed pure Velo memory copy with word-aligned fast paths.',
        example: 'mem.copy(@target, @source, 128)'
      },
      {
        name: 'mem.zero',
        signature: 'act mem.zero(dst: @void, byte_count: usize)',
        description: 'Zeroes out a block of memory.',
        example: 'mem.zero(@state, sizeof(State))'
      }
    ],
    types: [
      {
        name: 'Allocator',
        definition: 'data Allocator { alloc: act(usize) -> @void, free: act(@void) -> void }',
        description: 'Standard interface for custom allocators (Arena, Slab, FixedPool).'
      }
    ]
  },
  {
    name: 'std.fmt',
    category: 'Formatting & Text',
    tier: 1,
    description: 'Zero-dependency pure-Velo integer, float, and buffer formatting without sprintf or format string vulnerabilities.',
    pureVelo: true,
    loc: 1820,
    functions: [
      {
        name: 'fmt.int_to_str',
        signature: 'act fmt.int_to_str(val: i64, buf: @u8, buf_len: usize) -> usize',
        description: 'Converts a signed 64-bit integer into ASCII bytes within the caller-provided buffer (itoa).',
        example: 'mut buf: [32]u8; let len = fmt.int_to_str(12345, @buf, 32)'
      },
      {
        name: 'fmt.uint_to_hex',
        signature: 'act fmt.uint_to_hex(val: u64, buf: @u8, buf_len: usize) -> usize',
        description: 'Formats an unsigned integer into lowercase or uppercase hexadecimal representation.',
        example: 'let len = fmt.uint_to_hex(0xDEADBEEF, @buf, 32)'
      },
      {
        name: 'fmt.float_to_str',
        signature: 'act fmt.float_to_str(val: f64, precision: i32, buf: @u8, buf_len: usize) -> usize',
        description: 'Fast Grisu float-to-string conversion with configurable decimal precision.',
        example: 'let len = fmt.float_to_str(3.14159, 2, @buf, 32)'
      },
      {
        name: 'fmt.parse_i64',
        signature: 'act fmt.parse_i64(src: string) -> i64',
        description: 'Parses ASCII string representation into a 64-bit signed integer.',
        example: 'let n = fmt.parse_i64("42000")'
      }
    ]
  },
  {
    name: 'std.str',
    category: 'String Subsystem',
    tier: 1,
    description: 'Zero-allocation StrSlice non-owning byte views, branchless UTF-8 validators, Boyer-Moore search, and dynamic StrBuilder.',
    pureVelo: true,
    loc: 2150,
    functions: [
      {
        name: 'str.slice',
        signature: 'act str.slice(src: string, start: usize, end: usize) -> StrSlice',
        description: 'Creates a non-allocating window (pointer + length) into an existing string.',
        example: 'let sub = str.slice("hello world", 0, 5) // "hello"'
      },
      {
        name: 'str.find',
        signature: 'act str.find(haystack: string, needle: string) -> isize',
        description: 'Searches for needle substring using Boyer-Moore-Horspool algorithm. Returns -1 if not found.',
        example: 'let idx = str.find("the quick brown fox", "quick") // 4'
      },
      {
        name: 'str.starts_with',
        signature: 'act str.starts_with(src: string, prefix: string) -> bool',
        description: 'Checks if a string begins with the specified prefix without allocating memory.',
        example: 'if str.starts_with(line, "# ") { ... }'
      },
      {
        name: 'str.builder_create',
        signature: 'act str.builder_create(initial_capacity: usize) -> StrBuilder',
        description: 'Creates a high-performance resizable string accumulation buffer.',
        example: 'mut sb = str.builder_create(256); sb.append("Velo")'
      }
    ],
    types: [
      {
        name: 'StrSlice',
        definition: 'data StrSlice { ptr: @u8, len: usize }',
        description: 'Non-allocating read-only window into a UTF-8 character sequence.'
      }
    ]
  },
  {
    name: 'std.io',
    category: 'I/O & Streams',
    tier: 1,
    description: 'Ring-buffered stream readers and writers wrapping native OS handles. Eliminates C stdio.h FILE* overhead.',
    pureVelo: true,
    loc: 1640,
    functions: [
      {
        name: 'io.println',
        signature: 'act io.println(msg: string)',
        description: 'Prints a string followed by a newline directly to the standard output handle.',
        example: 'io.println("Server running on port {port}")'
      },
      {
        name: 'io.print',
        signature: 'act io.print(msg: string)',
        description: 'Prints a string without trailing newline.',
        example: 'io.print("Processing... ")'
      },
      {
        name: 'io.read_line',
        signature: 'act io.read_line(buf: @u8, max_len: usize) -> usize',
        description: 'Reads a line of user input from standard input.',
        example: 'mut buf: [128]u8; let len = io.read_line(@buf, 128)'
      }
    ]
  },
  {
    name: 'std.fs',
    category: 'Filesystem',
    tier: 1,
    description: 'Path normalization, directory iteration, chunked reading, and atomic file operations without C dirent.h.',
    pureVelo: true,
    loc: 2890,
    functions: [
      {
        name: 'fs.read_file',
        signature: 'act fs.read_file(path: string) -> string',
        description: 'Reads entire file into null-terminated heap buffer. Return is freed by caller.',
        example: 'let text = fs.read_file("config.json"); defer mem.free(text)'
      },
      {
        name: 'fs.write_file',
        signature: 'act fs.write_file(path: string, content: string) -> bool',
        description: 'Writes string content to a file. Overwrites existing files atomically.',
        example: 'fs.write_file("out.txt", "Velo build success")'
      },
      {
        name: 'fs.exists',
        signature: 'act fs.exists(path: string) -> bool',
        description: 'Queries filesystem metadata to test whether a file or directory exists.',
        example: 'if fs.exists("main.vl") { ... }'
      },
      {
        name: 'fs.size',
        signature: 'act fs.size(path: string) -> usize',
        description: 'Returns file size in bytes without reading file content into memory.',
        example: 'let bytes = fs.size("app.exe")'
      }
    ]
  },
  {
    name: 'std.coll',
    category: 'Collections',
    tier: 1,
    description: 'Core memory-conscious dynamic data structures: dynamic shelves, open-addressing hash maps, and ring buffers.',
    pureVelo: true,
    loc: 3120,
    functions: [
      {
        name: 'shelf.put',
        signature: 'act xs.put(item: T)',
        description: 'Appends item to the dynamic shelf, resizing the contiguous buffer if needed.',
        example: 'xs.put(42)'
      },
      {
        name: 'shelf.take',
        signature: 'act xs.take() -> T',
        description: 'Pops and returns the last element from the dynamic shelf in O(1) time.',
        example: 'let last = xs.take()'
      },
      {
        name: 'map.set',
        signature: 'act m.set(key: K, val: V)',
        description: 'Inserts or updates an entry in the open-addressing hash table.',
        example: 'scores.set("player1", 100)'
      },
      {
        name: 'map.get',
        signature: 'act m.get(key: K) -> @V',
        description: 'Looks up a key in the hash table. Returns pointer to value or null if absent.',
        example: 'let p = scores.get("player1")'
      }
    ],
    types: [
      {
        name: 'shelf[T]',
        definition: 'Dynamic growable array with bounds checking and snapshot iteration.',
        description: 'Core contiguous dynamic array in Velo.'
      },
      {
        name: 'map[K, V]',
        definition: 'Open-addressing hash table with Robin Hood hashing and tombstone deletion.',
        description: 'High-performance key-value mapping.'
      },
      {
        name: 'ring[T]',
        definition: 'Cache-friendly circular ring buffer and double-ended FIFO/LIFO queue.',
        description: 'Zero-reallocation bounded queue.'
      },
      {
        name: 'bitset[N]',
        definition: 'Dense bitfield supporting hardware population counts and bitwise operations.',
        description: 'Fixed-capacity bit array.'
      }
    ]
  },
  {
    name: 'std.math',
    category: 'Mathematics',
    tier: 1,
    description: 'Pure-Velo integer arithmetic, bit-manipulation intrinsics (clz, ctz, popcount), and IEEE-754 algorithms.',
    pureVelo: true,
    loc: 1450,
    functions: [
      {
        name: 'math.popcount',
        signature: 'act math.popcount(n: u64) -> i32',
        description: 'Returns the number of set bits (population count) using hardware instruction.',
        example: 'let count = math.popcount(0b10110010) // 4'
      },
      {
        name: 'math.clz',
        signature: 'act math.clz(n: u32) -> i32',
        description: 'Counts leading zeros in a 32-bit unsigned integer.',
        example: 'let zeros = math.clz(16)'
      },
      {
        name: 'math.sqrt',
        signature: 'act math.sqrt(val: f64) -> f64',
        description: 'Calculates the square root of a floating-point number.',
        example: 'let s = math.sqrt(144.0)'
      },
      {
        name: 'math.min',
        signature: 'act math.min[T](a: T, b: T) -> T',
        description: 'Returns the smaller of two numbers.',
        example: 'let m = math.min(10, 20)'
      }
    ]
  },
  {
    name: 'std.os',
    category: 'Operating System',
    tier: 1,
    description: 'Process spawning, anonymous inter-process pipes, environment variables, and CLI arguments for Windows and POSIX.',
    pureVelo: true,
    loc: 1980,
    functions: [
      {
        name: 'os.args',
        signature: 'act os.args() -> shelf[string]',
        description: 'Returns the array of command-line arguments passed to the current process.',
        example: 'let args = os.args()'
      },
      {
        name: 'os.get_env',
        signature: 'act os.get_env(key: string) -> string',
        description: 'Retrieves the value of an environment variable.',
        example: 'let path = os.get_env("PATH")'
      },
      {
        name: 'os.spawn',
        signature: 'act os.spawn(cmd: string, args: shelf[string]) -> Process',
        description: 'Spawns a child process with redirected stdout/stderr pipes without calling system().',
        example: 'let proc = os.spawn("gcc", shelf["-O2", "main.c"])'
      }
    ]
  },
  {
    name: 'std.json',
    category: 'Serialization',
    tier: 1,
    description: 'Zero-allocation JSON streaming tokenizer, DOM representation, serializer, and pretty-printer in pure Velo.',
    pureVelo: true,
    loc: 2310,
    functions: [
      {
        name: 'json.parse',
        signature: 'act json.parse(json_str: string) -> JsonValue',
        description: 'Parses a JSON string into an AST DOM node representation.',
        example: 'let doc = json.parse("{\\"name\\": \\"Velo\\", \\"version\\": 2}")'
      },
      {
        name: 'json.stringify',
        signature: 'act json.stringify(val: @JsonValue) -> string',
        description: 'Serializes a JSON AST tree into an optimized JSON string.',
        example: 'let text = json.stringify(@doc)'
      }
    ]
  },
  {
    name: 'std.time',
    category: 'Time & Clocks',
    tier: 1,
    description: 'Monotonic nanosecond timers, high-precision sleep, CPU cycle counters, and calendar calculations.',
    pureVelo: true,
    loc: 1120,
    functions: [
      {
        name: 'time.now',
        signature: 'act time.now() -> u64',
        description: 'Returns monotonic time in nanoseconds for high-precision benchmarking.',
        example: 'let start = time.now()'
      },
      {
        name: 'time.sleep_ms',
        signature: 'act time.sleep_ms(ms: u32)',
        description: 'Suspends execution of the current thread for the specified milliseconds.',
        example: 'time.sleep_ms(16) // 60 FPS frame delay'
      }
    ]
  },
  {
    name: 'std.simd',
    category: 'Hardware Acceleration',
    tier: 1,
    description: 'Direct bindings to 128-bit hardware vector instructions: dot products, square roots, clamps, and lane permutations.',
    pureVelo: true,
    loc: 890,
    functions: [
      {
        name: 'simd.dot',
        signature: 'act simd.dot(a: f32x4, b: f32x4) -> f32',
        description: 'Calculates the horizontal dot product of two 4-lane float vectors using single-instruction FMA.',
        example: 'let d = simd.dot(pos, normal)'
      },
      {
        name: 'simd.sqrt',
        signature: 'act simd.sqrt(v: f32x4) -> f32x4',
        description: 'Performs hardware vectorized square root across all 4 vector lanes simultaneously.',
        example: 'let roots = simd.sqrt(vectors)'
      },
      {
        name: 'simd.min',
        signature: 'act simd.min(a: f32x4, b: f32x4) -> f32x4',
        description: 'Computes per-lane minimum of two vectors in a single CPU cycle.',
        example: 'let clamped = simd.min(val, max_val)'
      }
    ]
  },

  // ================= TIER 2: EXTENDED ECOSYSTEM (A-Z) =================
  {
    name: 'std.async',
    category: 'Concurrency & Async',
    tier: 2,
    description: 'Cooperative lightweight task schedulers, future/promise combinators, and event loops.',
    pureVelo: true,
    functions: [
      {
        name: 'async.spawn',
        signature: 'act async.spawn(task: act() -> void) -> TaskHandle',
        description: 'Schedules a cooperative task on the thread event loop.',
        example: 'async.spawn(handle_connection)'
      }
    ]
  },
  {
    name: 'std.atomic',
    category: 'Concurrency & Low-Level',
    tier: 2,
    description: 'Hardware atomic primitives: load, store, compare-and-swap (CAS), and fetch-and-add.',
    pureVelo: true,
    functions: [
      {
        name: 'atomic.cas_i32',
        signature: 'act atomic.cas_i32(ptr: @i32, expected: i32, desired: i32) -> bool',
        description: 'Performs atomic compare-and-swap with sequentially consistent ordering.',
        example: 'let ok = atomic.cas_i32(@lock_val, 0, 1)'
      }
    ]
  },
  {
    name: 'std.crypto',
    category: 'Security & Cryptography',
    tier: 2,
    description: 'Pure-Velo implementations of SHA-256, HMAC, ChaCha20, and CSPRNG random bytes.',
    pureVelo: true,
    functions: [
      {
        name: 'crypto.sha256',
        signature: 'act crypto.sha256(data: @u8, len: usize, out_hash: @u8)',
        description: 'Computes the 256-bit cryptographic digest of input buffer.',
        example: 'crypto.sha256(@bytes, len, @hash_buf)'
      }
    ]
  },
  {
    name: 'std.net',
    category: 'Networking & Sockets',
    tier: 2,
    description: 'Cross-platform TCP and UDP socket networking, client/server connection streams, and IP address manipulation.',
    pureVelo: true,
    loc: 520,
    functions: [
      {
        name: 'tcp_listen',
        signature: 'act tcp_listen(ip: string, port: u16) -> @TcpListener',
        description: 'Binds a TCP socket and starts listening for incoming client connections with automatic address reuse.',
        example: 'let listener = tcp_listen("127.0.0.1", 8080)'
      },
      {
        name: 'tcp_accept',
        signature: 'act tcp_accept(listener: @TcpListener) -> @TcpStream',
        description: 'Accepts an incoming TCP connection from the listener and returns a connected TcpStream.',
        example: 'let stream = tcp_accept(listener)'
      },
      {
        name: 'tcp_connect',
        signature: 'act tcp_connect(ip: string, port: u16) -> @TcpStream',
        description: 'Establishes an active TCP connection to a remote IP address and port.',
        example: 'let client = tcp_connect("127.0.0.1", 8080)'
      },
      {
        name: 'tcp_write_str',
        signature: 'act tcp_write_str(stream: @TcpStream, text: string) -> i32',
        description: 'Sends a string message across the connected TCP stream. Returns number of bytes sent or -1 on error.',
        example: 'tcp_write_str(stream, "HTTP/1.1 200 OK\\r\\n\\r\\nHello!")'
      },
      {
        name: 'tcp_read_str',
        signature: 'act tcp_read_str(stream: @TcpStream, max_len: usize) -> string',
        description: 'Reads up to max_len bytes from the stream into a newly allocated null-terminated string.',
        example: 'let request = tcp_read_str(stream, 4096)'
      },
      {
        name: 'udp_bind',
        signature: 'act udp_bind(ip: string, port: u16) -> @UdpSocket',
        description: 'Binds a UDP socket to a local address and port for connectionless datagram transmission.',
        example: 'let sock = udp_bind("0.0.0.0", 9999)'
      },
      {
        name: 'udp_send_str_to',
        signature: 'act udp_send_str_to(sock: @UdpSocket, text: string, dest_ip: string, dest_port: u16) -> i32',
        description: 'Transmits a string datagram to a remote destination IP and port.',
        example: 'udp_send_str_to(sock, "PING", "127.0.0.1", 9999)'
      },
      {
        name: 'udp_recv_str_from',
        signature: 'act udp_recv_str_from(sock: @UdpSocket, max_len: usize, out_addr: @SocketAddr) -> string',
        description: 'Receives an incoming datagram as a string and captures sender endpoint information.',
        example: 'let packet = udp_recv_str_from(sock, 1024, @sender)'
      },
      {
        name: 'net_parse_ipv4',
        signature: 'act net_parse_ipv4(ip: string) -> u32',
        description: 'Parses an IPv4 string ("127.0.0.1", "localhost") into 32-bit network byte order.',
        example: 'let raw_ip = net_parse_ipv4("127.0.0.1")'
      },
      {
        name: 'net_format_ipv4',
        signature: 'act net_format_ipv4(addr: u32) -> string',
        description: 'Formats a 32-bit network-byte-order IPv4 address into a dotted decimal string.',
        example: 'let ip_str = net_format_ipv4(raw_ip)'
      }
    ]
  },
  {
    name: 'std.crypto',
    category: 'Security & Cryptography',
    tier: 1,
    description: 'Pure Velo cryptographic primitives: FIPS 180-4 SHA-256, RFC 1321 MD5, IEEE 802.3 CRC-32, RFC 2104 HMAC-SHA256, Hex encoding/decoding, and OS kernel CSPRNG.',
    pureVelo: true,
    functions: [
      {
        name: 'sha256_hash_str',
        signature: 'act sha256_hash_str(text: string) -> string',
        description: 'Computes a 64-character lowercase hexadecimal SHA-256 digest of a string.',
        example: 'let hash = sha256_hash_str("Hello, Velo!")'
      },
      {
        name: 'md5_hash_str',
        signature: 'act md5_hash_str(text: string) -> string',
        description: 'Computes a 32-character lowercase hexadecimal MD5 checksum of a string.',
        example: 'let md5sum = md5_hash_str("payload")'
      },
      {
        name: 'crc32_hash_str',
        signature: 'act crc32_hash_str(text: string) -> u32',
        description: 'Computes an IEEE 802.3 32-bit Cyclic Redundancy Check (CRC-32) checksum of a string.',
        example: 'let crc = crc32_hash_str("123456789")'
      },
      {
        name: 'crc32_hex',
        signature: 'act crc32_hex(val: u32) -> string',
        description: 'Formats a 32-bit CRC checksum into an 8-character lowercase hexadecimal string.',
        example: 'let hex_crc = crc32_hex(crc)'
      },
      {
        name: 'hmac_sha256_str',
        signature: 'act hmac_sha256_str(key: string, data: string) -> string',
        description: 'Computes an RFC 2104 HMAC-SHA256 message authentication code as a 64-character hex string.',
        example: 'let sig = hmac_sha256_str("secret-key", "request-payload")'
      },
      {
        name: 'crypto_random_bytes',
        signature: 'act crypto_random_bytes(buf: @u8, len: usize) -> bool',
        description: 'Fills a byte buffer with cryptographically secure random bytes from the OS kernel entropy source.',
        example: 'crypto_random_bytes(key_buf, 32)'
      },
      {
        name: 'crypto_random_u32',
        signature: 'act crypto_random_u32() -> u32',
        description: 'Generates a cryptographically secure random unsigned 32-bit integer.',
        example: 'let id = crypto_random_u32()'
      },
      {
        name: 'crypto_random_u64',
        signature: 'act crypto_random_u64() -> u64',
        description: 'Generates a cryptographically secure random unsigned 64-bit integer.',
        example: 'let token = crypto_random_u64()'
      },
      {
        name: 'crypto_random_range',
        signature: 'act crypto_random_range(min: u64, max: u64) -> u64',
        description: 'Generates a cryptographically secure uniform random integer in [min, max] without modulo bias.',
        example: 'let roll = crypto_random_range(1, 6)'
      },
      {
        name: 'crypto_random_hex',
        signature: 'act crypto_random_hex(byte_count: usize) -> string',
        description: 'Generates a secure random hexadecimal string (e.g. for session tokens or UUIDs).',
        example: 'let nonce = crypto_random_hex(16)'
      },
      {
        name: 'bytes_to_hex',
        signature: 'act bytes_to_hex(bytes: @u8, len: usize) -> string',
        description: 'Encodes raw bytes into a lowercase hexadecimal string.',
        example: 'let hex = bytes_to_hex(raw_buf, 32)'
      },
      {
        name: 'hex_to_bytes',
        signature: 'act hex_to_bytes(hex_str: string, out_bytes: @u8, max_len: usize) -> usize',
        description: 'Decodes a hexadecimal string into an output byte buffer.',
        example: 'let decoded = hex_to_bytes("a1b2c3d4", buf, 4)'
      }
    ],
    types: [
      {
        name: 'Sha256State',
        definition: 'data Sha256State { h0: u32, h1: u32, ... total_bytes: u64 }',
        description: 'Streaming SHA-256 state context for multi-chunk incremental hashing.'
      },
      {
        name: 'Md5State',
        definition: 'data Md5State { a: u32, b: u32, c: u32, d: u32, ... total_bytes: u64 }',
        description: 'Streaming MD5 state context for multi-chunk incremental hashing.'
      }
    ]
  },
  {
    name: 'std.http',
    category: 'Networking & Web',
    tier: 1,
    description: 'Pure Velo HTTP/1.1 client and lightweight server subsystem built on std.net, featuring URL parsing, percent-encoding, header containers, and request/response dispatch.',
    pureVelo: true,
    functions: [
      {
        name: 'http_get',
        signature: 'act http_get(url_str: string) -> HttpResponse',
        description: 'Executes a synchronous HTTP GET request and returns parsed HttpResponse.',
        example: 'let res = http_get("http://127.0.0.1:8080/api/users")'
      },
      {
        name: 'http_post',
        signature: 'act http_post(url_str: string, content_type: string, body: string) -> HttpResponse',
        description: 'Executes a synchronous HTTP POST request with a request body payload.',
        example: 'let res = http_post("http://127.0.0.1:8080/api/items", "application/json", "{\\"id\\":1}")'
      },
      {
        name: 'http_parse_url',
        signature: 'act http_parse_url(url_str: string) -> HttpUrl',
        description: 'Parses full URL into scheme, host, port, path, and query components.',
        example: 'let u = http_parse_url("http://localhost:8080/search?q=velo")'
      },
      {
        name: 'url_encode',
        signature: 'act url_encode(text: string) -> string',
        description: 'Encodes a string using RFC 3986 percent-encoding.',
        example: 'let enc = url_encode("hello world & co")'
      },
      {
        name: 'url_decode',
        signature: 'act url_decode(encoded: string) -> string',
        description: 'Decodes percent-encoded string (%XX and +).',
        example: 'let dec = url_decode(enc)'
      },
      {
        name: 'http_status_text',
        signature: 'act http_status_text(code: u16) -> string',
        description: 'Returns canonical RFC reason phrase for an HTTP status code.',
        example: 'let phrase = http_status_text(200)'
      },
      {
        name: 'http_server_listen',
        signature: 'act http_server_listen(ip: string, port: u16) -> @HttpServer',
        description: 'Binds and starts an HTTP server listener on an IP and port.',
        example: 'let server = http_server_listen("127.0.0.1", 8080)'
      },
      {
        name: 'http_server_accept',
        signature: 'act http_server_accept(server: @HttpServer, out_client: @@TcpStream, out_req: @HttpRequest) -> bool',
        description: 'Accepts an incoming client connection and parses HTTP request.',
        example: 'let ok = http_server_accept(server, @client, @req)'
      },
      {
        name: 'http_respond_json',
        signature: 'act http_respond_json(stream: @TcpStream, status: u16, json: string) -> bool',
        description: 'Sends JSON response with Content-Type application/json; charset=utf-8.',
        example: 'http_respond_json(client, 200, "{\\"status\\":\\"ok\\"}")'
      },
      {
        name: 'http_respond_text',
        signature: 'act http_respond_text(stream: @TcpStream, status: u16, text: string) -> bool',
        description: 'Sends plain text response with Content-Type text/plain; charset=utf-8.',
        example: 'http_respond_text(client, 200, "OK")'
      },
      {
        name: 'http_respond_html',
        signature: 'act http_respond_html(stream: @TcpStream, status: u16, html: string) -> bool',
        description: 'Sends HTML response with Content-Type text/html; charset=utf-8.',
        example: 'http_respond_html(client, 200, "<h1>Hello Velo</h1>")'
      }
    ],
    types: [
      {
        name: 'HttpUrl',
        definition: 'data HttpUrl { scheme: string, host: string, port: u16, path: string, query: string }',
        description: 'Parsed URL components.'
      },
      {
        name: 'HttpRequest',
        definition: 'data HttpRequest { method: string, path: string, version: string, headers: HttpHeaderMap, body: string, content_length: usize }',
        description: 'HTTP request representation.'
      },
      {
        name: 'HttpResponse',
        definition: 'data HttpResponse { status_code: u16, status_text: string, version: string, headers: HttpHeaderMap, body: string, content_length: usize }',
        description: 'HTTP response representation.'
      }
    ]
  },
  {
    name: 'std.log',
    category: 'Diagnostics & Telemetry',
    tier: 1,
    description: 'Structured logging framework with configurable severity levels (TRACE, DEBUG, INFO, WARN, ERROR, FATAL), ANSI terminal colorization, file appenders, and memory sinks.',
    pureVelo: true,
    functions: [
      {
        name: 'info',
        signature: 'act info(msg: string)',
        description: 'Logs an informational message to the active log sinks.',
        example: 'info("HTTP server listening on 127.0.0.1:8080")'
      },
      {
        name: 'warn',
        signature: 'act warn(msg: string)',
        description: 'Logs a warning message with yellow ANSI highlight.',
        example: 'warn("Disk space is below 15%")'
      },
      {
        name: 'error',
        signature: 'act error(msg: string)',
        description: 'Logs an error message with red ANSI highlight.',
        example: 'error("Failed to parse incoming payload")'
      },
      {
        name: 'debug',
        signature: 'act debug(msg: string)',
        description: 'Logs a diagnostic debug message (visible when log level <= LOG_DEBUG).',
        example: 'debug("Connection pool size: 8")'
      },
      {
        name: 'fatal',
        signature: 'act fatal(msg: string)',
        description: 'Logs a critical fatal failure with bold red highlight.',
        example: 'fatal("Unrecoverable database corruption")'
      },
      {
        name: 'log_info',
        signature: 'act log_info(target: string, msg: string)',
        description: 'Logs an INFO message with an explicit module/subsystem target label.',
        example: 'log_info("auth", "User admin logged in successfully")'
      },
      {
        name: 'log_set_level',
        signature: 'act log_set_level(level: u8)',
        description: 'Filters out log records below the specified severity threshold (LOG_TRACE..LOG_OFF).',
        example: 'log_set_level(LOG_WARN)'
      },
      {
        name: 'log_set_file',
        signature: 'act log_set_file(path: string)',
        description: 'Enables automatic file output appending uncolorized logs to the given path.',
        example: 'log_set_file("app.log")'
      },
      {
        name: 'log_enable_colors',
        signature: 'act log_enable_colors(enable: bool)',
        description: 'Toggles ANSI terminal color codes on console log output.',
        example: 'log_enable_colors(false)'
      }
    ],
    types: [
      {
        name: 'LogRecord',
        definition: 'data LogRecord { level: u8, target: string, message: string, timestamp: string }',
        description: 'Structured log record representation.'
      }
    ]
  },
  {
    name: 'std.test',
    category: 'Quality Assurance',
    tier: 2,
    description: 'Native integrated unit testing, assertion framework, suite lifecycle runner, and micro-benchmark profiler.',
    pureVelo: true,
    functions: [
      {
        name: 'assert',
        signature: 'act assert(cond: bool, msg: string) -> bool',
        description: 'Evaluates condition. Records pass if true, or records diagnostic failure if false.',
        example: 'assert(res == 40.0, "vector dot product mismatch")'
      },
      {
        name: 'assert_abort',
        signature: 'act assert_abort(cond: bool, msg: string) -> void',
        description: 'Hard assertion check. Terminates process immediately via os.exit(1) on failure.',
        example: 'assert_abort(ptr != null, "buffer allocation cannot be null")'
      },
      {
        name: 'assert_true',
        signature: 'act assert_true(cond: bool, msg: string) -> bool',
        description: 'Asserts that condition evaluates to true.',
        example: 'assert_true(items.len > 0, "collection must not be empty")'
      },
      {
        name: 'assert_false',
        signature: 'act assert_false(cond: bool, msg: string) -> bool',
        description: 'Asserts that condition evaluates to false.',
        example: 'assert_false(socket.is_closed(), "socket must remain open")'
      },
      {
        name: 'assert_eq_i64',
        signature: 'act assert_eq_i64(actual: i64, expected: i64, msg: string) -> bool',
        description: 'Asserts equality between two signed 64-bit integers with mismatch reporting.',
        example: 'assert_eq_i64(calc_balance(), 1000, "balance must match")'
      },
      {
        name: 'assert_ne_i64',
        signature: 'act assert_ne_i64(actual: i64, expected: i64, msg: string) -> bool',
        description: 'Asserts inequality between two signed 64-bit integers.',
        example: 'assert_ne_i64(status, -1, "status code cannot be error")'
      },
      {
        name: 'assert_eq_u64',
        signature: 'act assert_eq_u64(actual: u64, expected: u64, msg: string) -> bool',
        description: 'Asserts equality between two unsigned 64-bit integers.',
        example: 'assert_eq_u64(header.magic, 0x564C4F, "magic header check")'
      },
      {
        name: 'assert_eq_f64',
        signature: 'act assert_eq_f64(actual: f64, expected: f64, epsilon: f64, msg: string) -> bool',
        description: 'Asserts equality between two 64-bit floats within an epsilon tolerance threshold.',
        example: 'assert_eq_f64(pi_approx, 3.14159, 0.0001, "pi convergence")'
      },
      {
        name: 'assert_eq_str',
        signature: 'act assert_eq_str(actual: string, expected: string, msg: string) -> bool',
        description: 'Asserts string equality with detailed diagnostic diff formatting.',
        example: 'assert_eq_str(req.method, "GET", "HTTP method mismatch")'
      },
      {
        name: 'assert_ne_str',
        signature: 'act assert_ne_str(actual: string, expected: string, msg: string) -> bool',
        description: 'Asserts that two strings are not equal.',
        example: 'assert_ne_str(token, "", "auth token must not be empty")'
      },
      {
        name: 'assert_str_contains',
        signature: 'act assert_str_contains(haystack: string, needle: string, msg: string) -> bool',
        description: 'Asserts that haystack contains needle substring.',
        example: 'assert_str_contains(html, "<title>Velo</title>", "title tag present")'
      },
      {
        name: 'assert_str_starts_with',
        signature: 'act assert_str_starts_with(s: string, prefix: string, msg: string) -> bool',
        description: 'Asserts that string begins with specified prefix.',
        example: 'assert_str_starts_with(url, "https://", "must use secure scheme")'
      },
      {
        name: 'assert_str_ends_with',
        signature: 'act assert_str_ends_with(s: string, suffix: string, msg: string) -> bool',
        description: 'Asserts that string terminates with specified suffix.',
        example: 'assert_str_ends_with(filename, ".vl", "file extension check")'
      },
      {
        name: 'assert_null',
        signature: 'act assert_null(ptr: @u8, msg: string) -> bool',
        description: 'Asserts that a pointer is null.',
        example: 'assert_null(node.next, "tail node must have null next pointer")'
      },
      {
        name: 'assert_not_null',
        signature: 'act assert_not_null(ptr: @u8, msg: string) -> bool',
        description: 'Asserts that a pointer is not null.',
        example: 'assert_not_null(handle, "allocated handle must be valid")'
      },
      {
        name: 'test_suite_new',
        signature: 'act test_suite_new(name: string) -> TestSuite',
        description: 'Creates a new TestSuite runner instance with zeroed metrics.',
        example: 'mut s = test_suite_new("HTTP Parser Suite")'
      },
      {
        name: 'test_case',
        signature: 'act test_case(suite: @TestSuite, name: string, test_fn: act() -> void) -> void',
        description: 'Executes an isolated test function within the suite context and records results.',
        example: 'test_case(@s, "Status Parsing", test_status)'
      },
      {
        name: 'test_suite_finish',
        signature: 'act test_suite_finish(suite: @TestSuite) -> i32',
        description: 'Prints structured summary banner. Returns 0 if all cases passed, or 1 on failure.',
        example: 'return test_suite_finish(@s)'
      },
      {
        name: 'test_run',
        signature: 'act test_run(name: string, test_fn: act() -> void) -> bool',
        description: 'Runs a standalone test function under the global test runner.',
        example: 'test_run("Test Math", run_math_checks)'
      },
      {
        name: 'test_summary',
        signature: 'act test_summary() -> i32',
        description: 'Prints global test execution summary. Returns 0 on success, 1 on failure.',
        example: 'return test_summary()'
      },
      {
        name: 'test_reset',
        signature: 'act test_reset() -> void',
        description: 'Resets all global test case and assertion execution counters.',
        example: 'test_reset()'
      },
      {
        name: 'test_set_colors',
        signature: 'act test_set_colors(enable: bool) -> void',
        description: 'Toggles ANSI terminal color escape codes for test reporting.',
        example: 'test_set_colors(false)'
      },
      {
        name: 'test_benchmark',
        signature: 'act test_benchmark(name: string, iterations: usize, bench_fn: act() -> void) -> BenchmarkResult',
        description: 'Runs a micro-benchmark with warmup phase and computes nanoseconds per operation.',
        example: 'let res = test_benchmark("sha256_1kb", 10000, bench_sha256)'
      },
      {
        name: 'test_print_benchmark',
        signature: 'act test_print_benchmark(res: @BenchmarkResult) -> void',
        description: 'Prints formatted benchmark metrics (ops, ns/op, elapsed ms).',
        example: 'test_print_benchmark(@res)'
      }
    ],
    types: [
      {
        name: 'TestSuite',
        definition: 'data TestSuite { name: string, total_cases: usize, passed_cases: usize, failed_cases: usize, total_asserts: usize, passed_asserts: usize, failed_asserts: usize, verbose: bool }',
        description: 'Test suite lifecycle and metric tracking container.'
      },
      {
        name: 'BenchmarkResult',
        definition: 'data BenchmarkResult { name: string, iterations: usize, total_ms: u64, ns_per_op: u64 }',
        description: 'High-resolution benchmark performance measurement metrics.'
      }
    ]
  },
  {
    name: 'std.encoding',
    category: 'Serialization & Codecs',
    tier: 1,
    description: 'RFC 4648 Base64 (standard and URL-safe), RFC 4648 Base32, Hexadecimal (Base16), and binary integer serialization codecs.',
    pureVelo: true,
    functions: [
      {
        name: 'base64_encode',
        signature: 'act base64_encode(data: @u8, len: usize) -> string',
        description: 'Encodes raw binary buffer into an RFC 4648 standard Base64 string with padding.',
        example: 'let b64 = base64_encode(buf, len)'
      },
      {
        name: 'base64_encode_str',
        signature: 'act base64_encode_str(s: string) -> string',
        description: 'Encodes a string into an RFC 4648 standard Base64 string.',
        example: 'let b64 = base64_encode_str("username:password")'
      },
      {
        name: 'base64_decode',
        signature: 'act base64_decode(s: string, out_len: @usize) -> @u8',
        description: 'Decodes a Base64 string into a raw heap byte buffer.',
        example: 'let bytes = base64_decode(payload, @len)'
      },
      {
        name: 'base64_decode_str',
        signature: 'act base64_decode_str(s: string) -> string',
        description: 'Decodes a Base64 string directly into a heap-allocated UTF-8 string.',
        example: 'let text = base64_decode_str("aGVsbG8=")'
      },
      {
        name: 'base64_url_encode',
        signature: 'act base64_url_encode(data: @u8, len: usize, pad: bool) -> string',
        description: 'Encodes raw binary into an RFC 4648 URL-safe Base64 string (- and _) with optional padding.',
        example: 'let token = base64_url_encode(nonce, 32, false)'
      },
      {
        name: 'base64_url_encode_str',
        signature: 'act base64_url_encode_str(s: string, pad: bool) -> string',
        description: 'Encodes a string into an RFC 4648 URL-safe Base64 string.',
        example: 'let url_safe = base64_url_encode_str("query?k=v", false)'
      },
      {
        name: 'base64_url_decode',
        signature: 'act base64_url_decode(s: string, out_len: @usize) -> @u8',
        description: 'Decodes a URL-safe Base64 payload into a heap byte buffer.',
        example: 'let raw = base64_url_decode(jwt_part, @len)'
      },
      {
        name: 'base64_url_decode_str',
        signature: 'act base64_url_decode_str(s: string) -> string',
        description: 'Decodes a URL-safe Base64 string directly into a UTF-8 string.',
        example: 'let json_str = base64_url_decode_str(jwt_payload)'
      },
      {
        name: 'base64_is_valid',
        signature: 'act base64_is_valid(s: string) -> bool',
        description: 'Validates that a string is a properly formatted and padded Base64 representation.',
        example: 'if base64_is_valid(input) { ... }'
      },
      {
        name: 'base32_encode',
        signature: 'act base32_encode(data: @u8, len: usize) -> string',
        description: 'Encodes raw binary into an RFC 4648 Base32 string (A-Z, 2-7) with padding.',
        example: 'let secret = base32_encode(key_bytes, 10)'
      },
      {
        name: 'base32_encode_str',
        signature: 'act base32_encode_str(s: string) -> string',
        description: 'Encodes a string into an RFC 4648 Base32 string.',
        example: 'let b32 = base32_encode_str("velo")'
      },
      {
        name: 'base32_decode',
        signature: 'act base32_decode(s: string, out_len: @usize) -> @u8',
        description: 'Decodes a Base32 string into a raw heap byte buffer.',
        example: 'let key = base32_decode(totp_secret, @len)'
      },
      {
        name: 'base32_decode_str',
        signature: 'act base32_decode_str(s: string) -> string',
        description: 'Decodes a Base32 string directly into a UTF-8 string.',
        example: 'let orig = base32_decode_str("OZSWY3Y=")'
      },
      {
        name: 'base32_is_valid',
        signature: 'act base32_is_valid(s: string) -> bool',
        description: 'Validates that a string conforms to the RFC 4648 Base32 alphabet and padding.',
        example: 'if base32_is_valid(code) { ... }'
      },
      {
        name: 'hex_encode',
        signature: 'act hex_encode(data: @u8, len: usize, upper: bool) -> string',
        description: 'Encodes raw bytes into a lowercase or uppercase hexadecimal string.',
        example: 'let hex = hex_encode(digest, 32, false)'
      },
      {
        name: 'hex_encode_str',
        signature: 'act hex_encode_str(s: string, upper: bool) -> string',
        description: 'Encodes a string into a hexadecimal string.',
        example: 'let hex = hex_encode_str("hello", true)'
      },
      {
        name: 'hex_decode',
        signature: 'act hex_decode(s: string, out_len: @usize) -> @u8',
        description: 'Decodes a hexadecimal string into a heap byte buffer.',
        example: 'let bytes = hex_decode("deadbeef", @len)'
      },
      {
        name: 'hex_decode_str',
        signature: 'act hex_decode_str(s: string) -> string',
        description: 'Decodes a hexadecimal string directly into a UTF-8 string.',
        example: 'let str = hex_decode_str("48656c6c6f")'
      },
      {
        name: 'hex_is_valid',
        signature: 'act hex_is_valid(s: string) -> bool',
        description: 'Checks whether a string consists of an even number of valid hex characters.',
        example: 'if hex_is_valid(hash) { ... }'
      },
      {
        name: 'binary_put_u32_be',
        signature: 'act binary_put_u32_be(buf: @u8, val: u32) -> void',
        description: 'Serializes a 32-bit unsigned integer into a buffer in big-endian network byte order.',
        example: 'binary_put_u32_be(header, 0x12345678)'
      },
      {
        name: 'binary_get_u32_be',
        signature: 'act binary_get_u32_be(buf: @u8) -> u32',
        description: 'Deserializes a 32-bit unsigned integer from big-endian bytes.',
        example: 'let val = binary_get_u32_be(header)'
      },
      {
        name: 'binary_put_u64_le',
        signature: 'act binary_put_u64_le(buf: @u8, val: u64) -> void',
        description: 'Serializes a 64-bit unsigned integer into a buffer in little-endian order.',
        example: 'binary_put_u64_le(buf, 1000000)'
      },
      {
        name: 'binary_get_u64_le',
        signature: 'act binary_get_u64_le(buf: @u8) -> u64',
        description: 'Deserializes a 64-bit unsigned integer from little-endian bytes.',
        example: 'let val = binary_get_u64_le(buf)'
      }
    ]
  },
  {
    name: 'std.csv',
    category: 'Serialization & Codecs',
    tier: 1,
    description: 'RFC 4180 compliant streaming CSV record parser with zero-copy field views and arena-backed quote unescaping, plus a minimal-quoting record generator with LF / CRLF terminators.',
    pureVelo: true,
    functions: [
      {
        name: 'csv_reader_init',
        signature: 'act csv_reader_init(s: StrSlice) -> CsvReader',
        description: 'Initializes a streaming CSV reader over an in-memory byte range.',
        example: 'mut r = csv_reader_init(sb_to_slice(@sb))'
      },
      {
        name: 'csv_reader_init_str',
        signature: 'act csv_reader_init_str(s: string) -> CsvReader',
        description: 'Initializes a streaming CSV reader over a string.',
        example: 'mut r = csv_reader_init_str("id,name")'
      },
      {
        name: 'csv_read_record',
        signature: 'act csv_read_record(r: @CsvReader, arena: @Arena, out: @CsvRecord) -> bool',
        description: 'Parses the next RFC 4180 record into zero-copy field views. Returns false at end of input or after a recorded parse error.',
        example: 'loop csv_read_record(@r, @arena, @rec) { process(@rec) }'
      },
      {
        name: 'csv_record_field',
        signature: 'act csv_record_field(rec: @CsvRecord, index: usize) -> StrSlice',
        description: 'Returns the zero-copy byte view of the field at index, or an empty slice when out of bounds.',
        example: 'let name = csv_record_field(@rec, 1)'
      },
      {
        name: 'csv_record_field_str',
        signature: 'act csv_record_field_str(rec: @CsvRecord, index: usize, arena: @Arena) -> string',
        description: 'Materializes the field at index as a null-terminated string in arena memory.',
        example: "let name_str = csv_record_field_str(@rec, 1, @arena)"
      },
      {
        name: 'csv_record_field_quoted',
        signature: 'act csv_record_field_quoted(rec: @CsvRecord, index: usize) -> bool',
        description: 'Returns true when the field was quoted in the source document.',
        example: 'if csv_record_field_quoted(@rec, 0) { ... }'
      },
      {
        name: 'csv_reader_error_msg',
        signature: 'act csv_reader_error_msg(r: @CsvReader) -> StrSlice',
        description: 'Returns the recorded parse error message (empty when no error occurred).',
        example: 'let msg = csv_reader_error_msg(@r)'
      },
      {
        name: 'csv_writer_init',
        signature: 'act csv_writer_init(sb: @StrBuilder, use_crlf: bool) -> CsvWriter',
        description: 'Initializes a record writer over an arena-backed StrBuilder, emitting CRLF or LF record terminators.',
        example: 'mut w = csv_writer_init(@sb, true)'
      },
      {
        name: 'csv_writer_field',
        signature: 'act csv_writer_field(w: @CsvWriter, s: StrSlice)',
        description: 'Appends one field with automatic minimal RFC 4180 quoting and separator insertion.',
        example: 'csv_writer_field(@w, slice_from_str("v,1"))'
      },
      {
        name: 'csv_writer_field_str',
        signature: 'act csv_writer_field_str(w: @CsvWriter, s: string)',
        description: 'Appends one string field to the current record.',
        example: 'csv_writer_field_str(@w, "qty")'
      },
      {
        name: 'csv_writer_end_row',
        signature: 'act csv_writer_end_row(w: @CsvWriter)',
        description: 'Ends the current record with the configured terminator and resets the field counter.',
        example: 'csv_writer_end_row(@w)'
      },
      {
        name: 'csv_field_needs_quotes',
        signature: 'act csv_field_needs_quotes(s: StrSlice) -> bool',
        description: 'Checks whether field content (comma, quote, CR, LF) forces RFC 4180 quoting.',
        example: 'if csv_field_needs_quotes(field) { ... }'
      },
      {
        name: 'csv_escape_str',
        signature: 'act csv_escape_str(s: string) -> string',
        description: 'One-shot field serializer into a heap-allocated CSV-safe string.',
        example: 'let safe = csv_escape_str("say \"hi\"")'
      },
      {
        name: 'csv_make_row_str',
        signature: 'act csv_make_row_str(fields: @string, count: usize, use_crlf: bool) -> string',
        description: 'Serializes an array of fields into a single heap-allocated terminated CSV record string.',
        example: 'let row = csv_make_row_str(@fields, 3, false)'
      }
    ],
    types: [
      {
        name: 'CsvReader',
        definition: 'data CsvReader { src: StrSlice, pos: usize, row: usize, had_error: bool, err_row: usize, err_msg: StrSlice }',
        description: 'Streaming cursor over an in-memory CSV document with row numbering and error diagnostics.'
      },
      {
        name: 'CsvRecord',
        definition: 'data CsvRecord { row: usize, first: @CsvField, count: usize, ok: bool }',
        description: 'One parsed record: intrusive linked list of zero-copy field views with its 1-based row number.'
      },
      {
        name: 'CsvWriter',
        definition: 'data CsvWriter { sb: @StrBuilder, fields_in_row: usize, use_crlf: bool }',
        description: 'Record generator state tracking separator insertion and terminator mode.'
      }
    ]
  },
  {
    name: 'std.cli',
    category: 'System & Tooling',
    tier: 1,
    description: 'GNU-style command-line argument and flag parsing library with typed queries, subcommands, defaults, and automated --help formatting.',
    pureVelo: true,
    functions: [
      {
        name: 'cli_parser_init',
        signature: 'act cli_parser_init(arena: @Arena, args: @Args) -> CliContext',
        description: 'Initializes a CLI parser context with automatic --help/-h flag registered.',
        example: 'mut p = cli_parser_init(@arena, args_ptr)'
      },
      {
        name: 'cli_parser_program',
        signature: 'act cli_parser_program(p: @CliContext, program: string, description: string) -> void',
        description: 'Sets program name and description banner for usage rendering.',
        example: 'cli_parser_program(@p, "app", "demo utility")'
      },
      {
        name: 'cli_parser_version',
        signature: 'act cli_parser_version(p: @CliContext, version: string) -> void',
        description: 'Sets the application version string.',
        example: 'cli_parser_version(@p, "1.0.0")'
      },
      {
        name: 'cli_parser_flag',
        signature: 'act cli_parser_flag(p: @CliContext, long_name: string, short_name: string, takes_value: bool, required: bool, default_value: string, helps: string) -> bool',
        description: 'Registers a boolean or value-bearing flag with short alias and documentation.',
        example: 'cli_parser_flag(@p, "jobs", "j", true, false, "2", "worker count")'
      },
      {
        name: 'cli_parser_subcommand',
        signature: 'act cli_parser_subcommand(p: @CliContext, name: string, helps: string) -> bool',
        description: 'Registers a subcommand name and description for command routing.',
        example: 'cli_parser_subcommand(@p, "build", "compile targets")'
      },
      {
        name: 'cli_parse',
        signature: 'act cli_parse(p: @CliContext) -> bool',
        description: 'Executes parser against supplied argument tokens. Returns true on success, false on syntax or validation error.',
        example: 'if !cli_parse(@p) { cli_print_error(@p) }'
      },
      {
        name: 'cli_flag_bool',
        signature: 'act cli_flag_bool(p: @CliContext, name: string) -> bool',
        description: 'Checks whether a boolean flag was supplied on the command line.',
        example: 'let verbose = cli_flag_bool(@p, "verbose")'
      },
      {
        name: 'cli_flag_str',
        signature: 'act cli_flag_str(p: @CliContext, name: string) -> string',
        description: 'Retrieves the parsed value or default string for a value-bearing flag.',
        example: 'let path = cli_flag_str(@p, "output")'
      },
      {
        name: 'cli_flag_i64',
        signature: 'act cli_flag_i64(p: @CliContext, name: string, out: @i64) -> bool',
        description: 'Parses a flag value as a signed 64-bit integer.',
        example: 'cli_flag_i64(@p, "jobs", @jobs)'
      },
      {
        name: 'cli_subcommand',
        signature: 'act cli_subcommand(p: @CliContext) -> string',
        description: 'Returns the invoked subcommand name, or empty string if none.',
        example: 'let cmd = cli_subcommand(@p)'
      },
      {
        name: 'cli_positional_count',
        signature: 'act cli_positional_count(p: @CliContext) -> usize',
        description: 'Returns the count of non-flag positional arguments.',
        example: 'let argc = cli_positional_count(@p)'
      },
      {
        name: 'cli_positional',
        signature: 'act cli_positional(p: @CliContext, idx: usize) -> string',
        description: 'Retrieves the positional argument at the specified zero-based index.',
        example: 'let file = cli_positional(@p, 0)'
      },
      {
        name: 'cli_help_string',
        signature: 'act cli_help_string(p: @CliContext) -> string',
        description: 'Renders the complete aligned help table as a string.',
        example: 'let help_txt = cli_help_string(@p)'
      },
      {
        name: 'cli_print_help',
        signature: 'act cli_print_help(p: @CliContext) -> void',
        description: 'Prints the formatted help table to standard output.',
        example: 'cli_print_help(@p)'
      },
      {
        name: 'cli_print_version',
        signature: 'act cli_print_version(p: @CliContext) -> void',
        description: 'Prints program version to standard output.',
        example: 'cli_print_version(@p)'
      },
      {
        name: 'cli_print_error',
        signature: 'act cli_print_error(p: @CliContext) -> void',
        description: 'Prints syntax error diagnostics and helpful suggestions to standard error.',
        example: 'cli_print_error(@p)'
      }
    ],
    types: [
      {
        name: 'CliContext',
        definition: 'data CliContext { arena: @Arena, program: string, version: string, description: string, args: @Args, longs: @string, shorts: @string, ... }',
        description: 'Parser and execution result context storing registered definitions and parsed options.'
      }
    ]
  },
  {
    name: 'std.url',
    description: 'RFC 3986 URL parsing, building, percent-encoding, query parameters, and path joining.',
    functions: [
      {
        name: 'url_parse',
        signature: 'act url_parse(raw: string, out: @Url) -> bool',
        description: 'Parses an RFC 3986 URL or relative reference into a Url structure. Returns true on success.',
        example: 'mut u = url_new()\nif url_parse("https://user:pass@example.com:8080/path?q=1#frag", @u) {\n  io.println(u.host)\n}'
      },
      {
        name: 'url_parse_str',
        signature: 'act url_parse_str(raw: string) -> Url',
        description: 'Convenience helper that parses an RFC 3986 URL and returns the resulting Url struct.',
        example: 'let u = url_parse_str("https://example.com/api")'
      },
      {
        name: 'url_to_string',
        signature: 'act url_to_string(u: @Url) -> string',
        description: 'Serializes a Url structure back into its canonical RFC 3986 representation.',
        example: 'let href = url_to_string(@u)'
      },
      {
        name: 'url_encode',
        signature: 'act url_encode(text: string) -> string',
        description: 'Percent-encodes all characters except RFC 3986 unreserved characters (A-Z, a-z, 0-9, -, ., _, ~).',
        example: 'let enc = url_encode("hello world & velo") // "hello%20world%20%26%20velo"'
      },
      {
        name: 'url_decode',
        signature: 'act url_decode(encoded: string) -> string',
        description: 'Decodes a percent-encoded string, converting + to space and %XX to raw bytes.',
        example: 'let raw = url_decode("hello%20world")'
      },
      {
        name: 'url_query_escape',
        signature: 'act url_query_escape(text: string) -> string',
        description: 'Escapes a string for application/x-www-form-urlencoded format, encoding spaces as +.',
        example: 'let qe = url_query_escape("hello world") // "hello+world"'
      },
      {
        name: 'url_query_unescape',
        signature: 'act url_query_unescape(encoded: string) -> string',
        description: 'Decodes an application/x-www-form-urlencoded string.',
        example: 'let raw = url_query_unescape("hello+world")'
      },
      {
        name: 'url_path_escape',
        signature: 'act url_path_escape(path: string) -> string',
        description: 'Escapes a path segment, preserving slashes and sub-delimiters while encoding spaces as %20.',
        example: 'let pe = url_path_escape("/user profiles/all")'
      },
      {
        name: 'url_path_unescape',
        signature: 'act url_path_unescape(path: string) -> string',
        description: 'Decodes percent-encoded characters in a URL path without converting + to space.',
        example: 'let raw = url_path_unescape("/tags/c%2B%2B")'
      },
      {
        name: 'url_query_has',
        signature: 'act url_query_has(query: string, key: string) -> bool',
        description: 'Returns true if query contains the specified parameter key.',
        example: 'if url_query_has(u.raw_query, "sort") { ... }'
      },
      {
        name: 'url_query_get',
        signature: 'act url_query_get(query: string, key: string) -> string',
        description: 'Retrieves the decoded value of a query parameter by key, or null if not found.',
        example: 'let page = url_query_get(u.raw_query, "page")'
      },
      {
        name: 'url_query_set',
        signature: 'act url_query_set(query: string, key: string, val: string) -> string',
        description: 'Replaces or appends a key-value parameter in a query string.',
        example: 'let new_q = url_query_set(u.raw_query, "page", "2")'
      },
      {
        name: 'url_query_del',
        signature: 'act url_query_del(query: string, key: string) -> string',
        description: 'Removes all occurrences of a parameter key from a query string.',
        example: 'let clean_q = url_query_del(u.raw_query, "debug")'
      },
      {
        name: 'url_join_path',
        signature: 'act url_join_path(base_path: string, rel_path: string) -> string',
        description: 'Joins two path segments, ensuring exactly one slash separates them.',
        example: 'let full = url_join_path("/api/v1/", "/users") // "/api/v1/users"'
      },
      {
        name: 'url_port_or_default',
        signature: 'act url_port_or_default(u: @Url) -> i32',
        description: 'Returns explicit port if set, or the standard default port for http (80), https (443), ws (80), wss (443), ssh (22), or ftp (21).',
        example: 'let port = url_port_or_default(@u)'
      }
    ],
    types: [
      {
        name: 'Url',
        definition: 'data Url { scheme: string, username: string, password: string, host: string, hostname: string, port: i32, path: string, raw_query: string, fragment: string, is_absolute: bool, is_valid: bool }',
        description: 'RFC 3986 URI/URL decomposition structure holding scheme, credentials, host, port, path, query, and fragment.'
      },
      {
        name: 'UrlQueryParam',
        definition: 'data UrlQueryParam { key: string, val: string }',
        description: 'Key-value pair extracted from a query string.'
      }
    ]
  }
];

