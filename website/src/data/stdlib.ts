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
    name: 'std.test',
    category: 'Quality Assurance',
    tier: 2,
    description: 'Native integrated test assertion framework and benchmark test runner.',
    pureVelo: true,
    functions: [
      {
        name: 'assert',
        signature: 'act assert(cond: bool, msg: string)',
        description: 'Evaluates condition. Aborts process with location and diagnostic message if false.',
        example: 'assert(res == 40.0, "vector dot product mismatch")'
      }
    ]
  }
];

