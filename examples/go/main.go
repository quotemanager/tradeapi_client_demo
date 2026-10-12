// Local HTTP example. Run from repository root: go run ./examples/go/main.go tdx query funds
package main

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"regexp"
	"strings"
	"time"
)

type Spec struct {
	Method string `json:"method"`
	Path   string `json:"path"`
	Input  string `json:"input"`
	Live   bool   `json:"live"`
}
type Profile struct {
	BaseURL  string            `json:"base_url"`
	URLEnv   string            `json:"url_env"`
	TokenEnv string            `json:"token_env"`
	Queries  map[string]string `json:"queries"`
	Commands map[string]Spec   `json:"commands"`
}

func readObject(file string) (map[string]json.RawMessage, error) {
	data, err := os.ReadFile(file)
	if err != nil {
		return nil, err
	}
	if len(data) > 65536 {
		return nil, errors.New("JSON file exceeds 64 KiB")
	}
	data = bytes.TrimPrefix(data, []byte{0xef, 0xbb, 0xbf})
	var result map[string]json.RawMessage
	if err = json.Unmarshal(data, &result); err != nil {
		return nil, err
	}
	if result == nil {
		return nil, errors.New("expected JSON object")
	}
	return result, nil
}
func run(args []string) (int, error) {
	execute := false
	clean := []string{}
	for _, arg := range args {
		if arg == "--execute" {
			execute = true
		} else {
			clean = append(clean, arg)
		}
	}
	if len(clean) < 1 || len(clean) > 3 {
		return 1, errors.New("usage: demo PRODUCT [COMMAND [VALUE]] [--execute]")
	}
	product, command, value := clean[0], "query", ""
	if len(clean) > 1 {
		command = clean[1]
	}
	if len(clean) > 2 {
		value = clean[2]
	}
	rawProfiles, err := readObject("config/api-contract.json")
	if err != nil {
		return 1, err
	}
	if product != "tdx" && product != "ths" {
		return 1, errors.New("PRODUCT must be tdx or ths")
	}
	var profile Profile
	if err = json.Unmarshal(rawProfiles[product], &profile); err != nil {
		return 1, err
	}
	var spec Spec
	if command == "query" {
		category := value
		if category == "" {
			category = "funds"
		}
		path, ok := profile.Queries[category]
		if !ok {
			return 1, errors.New("unsupported query")
		}
		spec = Spec{Method: "GET", Path: path, Input: "none"}
	} else {
		var ok bool
		spec, ok = profile.Commands[command]
		if !ok {
			return 1, errors.New("unsupported command")
		}
	}
	var body any
	if spec.Input == "file" {
		body, err = readObject(value)
		if err != nil {
			return 1, err
		}
	} else if strings.HasPrefix(spec.Input, "id-") {
		if !regexp.MustCompile(`^[A-Za-z0-9_-]{1,128}$`).MatchString(value) {
			return 1, errors.New("pass an existing action/preview ID")
		}
		if spec.Input == "id-path" {
			spec.Path += value
		} else {
			body = map[string]string{"preview_id": value}
		}
	} else if value != "" && command != "query" {
		return 1, errors.New("this command takes no VALUE")
	}
	if spec.Live && !execute {
		data, _ := json.MarshalIndent(map[string]any{"dry_run": true, "method": spec.Method, "path": spec.Path, "body": body,
			"note": "Nothing sent. --execute submits ONE REAL action."}, "", "  ")
		fmt.Println(string(data))
		return 0, nil
	}
	base := os.Getenv(profile.URLEnv)
	if base == "" {
		base = profile.BaseURL
	}
	base = strings.TrimRight(base, "/")
	parsed, err := url.Parse(base)
	if err != nil || parsed.Scheme != "http" || parsed.Hostname() != "127.0.0.1" || parsed.Port() == "" ||
		parsed.User != nil || parsed.Path != "" || parsed.RawQuery != "" || parsed.Fragment != "" {
		return 1, errors.New("URL must be http://127.0.0.1:<port>")
	}
	token := strings.TrimSpace(os.Getenv(profile.TokenEnv))
	if spec.Path != "/health" && !regexp.MustCompile(`^[A-Za-z0-9_-]{32,256}$`).MatchString(token) {
		return 1, errors.New("set " + profile.TokenEnv)
	}
	var reader io.Reader
	if body != nil {
		data, e := json.Marshal(body)
		if e != nil {
			return 1, e
		}
		reader = bytes.NewReader(data)
	}
	request, err := http.NewRequest(spec.Method, base+spec.Path, reader)
	if err != nil {
		return 1, err
	}
	request.Header.Set("Content-Type", "application/json")
	if token != "" {
		request.Header.Set("Authorization", "Bearer "+token)
	}
	// Fresh, non-pooled connection: no proxy, redirect or application retry.
	transport := &http.Transport{Proxy: nil, DisableKeepAlives: true}
	defer transport.CloseIdleConnections()
	client := &http.Client{Transport: transport, Timeout: 90 * time.Second, CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse }}
	response, err := client.Do(request)
	if err != nil {
		return 1, err
	}
	defer response.Body.Close()
	data, err := io.ReadAll(io.LimitReader(response.Body, 16*1024*1024+1))
	if err != nil {
		return 1, err
	}
	if len(data) > 16*1024*1024 {
		return 1, errors.New("response exceeds 16 MiB")
	}
	var result map[string]json.RawMessage
	if err = json.Unmarshal(data, &result); err != nil {
		return 1, err
	}
	if result == nil {
		return 1, errors.New("invalid response object")
	}
	pretty, _ := json.MarshalIndent(result, "", "  ")
	fmt.Println("HTTP", response.StatusCode)
	fmt.Println(string(pretty))
	if response.StatusCode != 200 || string(result["ok"]) == "false" {
		return 1, nil
	}
	return 0, nil
}
func main() {
	code, err := run(os.Args[1:])
	if err != nil {
		fmt.Fprintln(os.Stderr, err, "\nNo automatic retry. Reconcile any submitted action in the official client.")
	}
	os.Exit(code)
}
