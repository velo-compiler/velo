// benchmark/server_go.go — HTTP benchmark server in Go
package main

import (
	"fmt"
	"net/http"
	"os"
)

func main() {
	port := "8080"
	if len(os.Args) > 1 && len(os.Args[1]) > 0 {
		port = os.Args[1]
	} else if p := os.Getenv("PORT"); p != "" {
		port = p
	}

	mux := http.NewServeMux()
	mux.HandleFunc("/plaintext", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Connection", "close")
		w.Header().Set("Content-Type", "text/plain; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("Hello, World!"))
	})
	mux.HandleFunc("/json", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Connection", "close")
		w.Header().Set("Content-Type", "application/json; charset=utf-8")
		w.WriteHeader(http.StatusOK)
		w.Write([]byte(`{"message":"Hello, World!","status":"ok"}`))
	})

	server := &http.Server{
		Addr:    "127.0.0.1:" + port,
		Handler: mux,
	}

	fmt.Printf("[Go] Server listening on http://127.0.0.1:%s\n", port)
	if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		fmt.Fprintf(os.Stderr, "[Go Error] %v\n", err)
	}
}
