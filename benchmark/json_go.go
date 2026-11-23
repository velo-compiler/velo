// benchmark/json_go.go — JSON parsing and aggregation benchmark in Go
package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strconv"
)

type Record struct {
	Id     int    `json:"id"`
	Name   string `json:"name"`
	Age    int    `json:"age"`
	Active bool   `json:"active"`
	Scores []int  `json:"scores"`
}

func runJsonBenchmark(payload string, iterations int) {
	totalActive := 0
	totalAge := 0
	totalScore := 0

	raw := []byte(payload)

	for it := 0; it < iterations; it++ {
		var records []Record
		if err := json.Unmarshal(raw, &records); err == nil {
			for _, rec := range records {
				if rec.Active {
					totalActive++
					totalAge += rec.Age
					if len(rec.Scores) > 0 {
						totalScore += rec.Scores[0]
					}
				}
			}
		}
	}

	fmt.Printf("Done %d iterations: active=%d, age=%d, score=%d\n", iterations, totalActive, totalAge, totalScore)
}

func main() {
	payload := `[{"id":1,"name":"Alice","age":28,"active":true,"scores":[85,92,78]},{"id":2,"name":"Bob","age":34,"active":false,"scores":[70,75,80]},{"id":3,"name":"Charlie","age":22,"active":true,"scores":[95,98,91]},{"id":4,"name":"Diana","age":41,"active":true,"scores":[88,84,90]},{"id":5,"name":"Evan","age":29,"active":false,"scores":[65,72,68]},{"id":6,"name":"Fiona","age":31,"active":true,"scores":[92,89,94]},{"id":7,"name":"George","age":50,"active":true,"scores":[79,83,85]},{"id":8,"name":"Hannah","age":26,"active":false,"scores":[81,77,86]},{"id":9,"name":"Ian","age":38,"active":true,"scores":[87,91,89]},{"id":10,"name":"Julia","age":24,"active":true,"scores":[96,94,99]}]`
	iters := 5000
	if len(os.Args) > 1 {
		if val, err := strconv.Atoi(os.Args[1]); err == nil {
			iters = val
		}
	}
	runJsonBenchmark(payload, iters)
}
