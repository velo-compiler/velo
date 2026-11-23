// benchmark/server_c.c — HTTP benchmark server in C
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
  #include <winsock2.h>
  #include <ws2tcpip.h>
  #pragma comment(lib, "ws2_32.lib")
  typedef int socklen_t;
#else
  #include <unistd.h>
  #include <sys/socket.h>
  #include <netinet/in.h>
  #include <arpa/inet.h>
  #define closesocket close
  #define INVALID_SOCKET -1
  #define SOCKET_ERROR -1
  typedef int SOCKET;
#endif

static const char* RESP_PLAINTEXT =
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain; charset=utf-8\r\n"
    "Content-Length: 13\r\n"
    "Connection: close\r\n\r\n"
    "Hello, World!";

static const char* RESP_JSON =
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: application/json; charset=utf-8\r\n"
    "Content-Length: 38\r\n"
    "Connection: close\r\n\r\n"
    "{\"message\":\"Hello, World!\",\"status\":\"ok\"}";

static const char* RESP_404 =
    "HTTP/1.1 404 Not Found\r\n"
    "Content-Type: text/plain; charset=utf-8\r\n"
    "Content-Length: 9\r\n"
    "Connection: close\r\n\r\n"
    "Not Found";

int main(int argc, char** argv) {
    int port = 8080;
    if (argc > 1 && argv[1]) {
        port = atoi(argv[1]);
        if (port <= 0) port = 8080;
    } else {
        const char* env_p = getenv("PORT");
        if (env_p) {
            int p = atoi(env_p);
            if (p > 0) port = p;
        }
    }

#ifdef _WIN32
    WSADATA wsa;
    if (WSAStartup(MAKEWORD(2, 2), &wsa) != 0) {
        fprintf(stderr, "[C Error] WSAStartup failed\n");
        return 1;
    }
#endif

    SOCKET server_fd = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_fd == INVALID_SOCKET) {
        fprintf(stderr, "[C Error] socket() failed\n");
        return 1;
    }

    int opt = 1;
    setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, (const char*)&opt, sizeof(opt));

    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = inet_addr("127.0.0.1");
    address.sin_port = htons((unsigned short)port);

    if (bind(server_fd, (struct sockaddr*)&address, sizeof(address)) == SOCKET_ERROR) {
        fprintf(stderr, "[C Error] bind() failed on port %d\n", port);
        closesocket(server_fd);
        return 1;
    }

    if (listen(server_fd, 128) == SOCKET_ERROR) {
        fprintf(stderr, "[C Error] listen() failed\n");
        closesocket(server_fd);
        return 1;
    }

    printf("[C] Server listening on http://127.0.0.1:%d\n", port);
    fflush(stdout);

    char buf[1024];
    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        SOCKET client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
        if (client_fd == INVALID_SOCKET) break;

        int bytes = recv(client_fd, buf, sizeof(buf) - 1, 0);
        if (bytes > 0) {
            buf[bytes] = '\0';
            if (strncmp(buf, "GET /plaintext", 14) == 0) {
                send(client_fd, RESP_PLAINTEXT, (int)strlen(RESP_PLAINTEXT), 0);
            } else if (strncmp(buf, "GET /json", 9) == 0) {
                send(client_fd, RESP_JSON, (int)strlen(RESP_JSON), 0);
            } else {
                send(client_fd, RESP_404, (int)strlen(RESP_404), 0);
            }
        }
        closesocket(client_fd);
    }

    closesocket(server_fd);
#ifdef _WIN32
    WSACleanup();
#endif
    return 0;
}
