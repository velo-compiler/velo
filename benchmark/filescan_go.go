// benchmark/filescan_go.go — File scanning & word count benchmark in Go
package main

import (
	"fmt"
	"os"
)

func scanFile(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return err
	}

	lines := 0
	words := 0
	inWord := false

	for _, b := range data {
		if b == '\n' {
			lines++
		}
		if b == ' ' || b == '\t' || b == '\n' || b == '\r' {
			inWord = false
		} else if !inWord {
			inWord = true
			words++
		}
	}

	fmt.Printf("Scanned: lines=%d, words=%d, bytes=%d\n", lines, words, len(data))
	return nil
}

func main() {
	target := "bootstrap.c"
	if len(os.Args) > 1 && len(os.Args[1]) > 0 {
		target = os.Args[1]
	}

	if err := scanFile(target); err != nil {
		fmt.Fprintf(os.Stderr, "[Go Error] %v\n", err)
		os.Exit(1)
	}
}
