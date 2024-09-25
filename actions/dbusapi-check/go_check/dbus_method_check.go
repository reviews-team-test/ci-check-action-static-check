package main

import (
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"io/ioutil"
	"log"
	"os"
	"path/filepath"
	"regexp"
	"strings"
	"bufio"
	"encoding/json"
)

// Result holds the final output structure
type Result struct {
	ProjectPath     string           `json:"project_path"`
	DBusMethodCount int              `json:"dbus_method_count"`
	UnsafeCallCount int              `json:"unsafe_call_count"`
	ScanResult      string           `json:"scan_result"`  // 新增字段
	Details         []UnsafeCallInfo `json:"details"`
}

// UnsafeCallInfo holds information about a single unsafe call
type UnsafeCallInfo struct {
	InterfaceName string   `json:"interface_name"`
	FunctionName  string   `json:"function_name"`
	Parameters    []string `json:"args"`
	UnsafeCall    string   `json:"unsafe_call"`
	CodeLine      int      `json:"code_line"`
	FilePath      string   `json:"file_path"`
	CodeContent   string   `json:"code_content"`
}

type CallGraph struct {
	Functions map[string]*ast.FuncDecl
	Calls     map[string][]string
	FileSet   *token.FileSet
}

// extractMethodNamesFromGoCode extracts method names from Go code if 'dbusutil.ExportedMethods' is present
func extractMethodNamesFromGoCode(goCode string) []string {
	var methodNames []string

	// Check if 'dbusutil.ExportedMethods' is present in the code
	if strings.Contains(goCode, "dbusutil.ExportedMethods") {
		// Define the regex pattern to extract method names
		namePattern := regexp.MustCompile(`Name:\s*"([^"]+)"`)
		names := namePattern.FindAllStringSubmatch(goCode, -1)

		for _, match := range names {
			if len(match) > 1 {
				methodNames = append(methodNames, match[1])
			}
		}
	}

	return methodNames
}

// extractMethodNamesFromFiles reads files and extracts method names
func extractMethodNamesFromFiles(filePaths []string) []string {
	var allMethodNames []string

	for _, filePath := range filePaths {
		data, err := ioutil.ReadFile(filePath)
		if err != nil {
			fmt.Printf("Error reading file %s: %v\n", filePath, err)
			continue
		}
		goCode := string(data)
		methodNames := extractMethodNamesFromGoCode(goCode)
		allMethodNames = append(allMethodNames, methodNames...)
	}

	return allMethodNames
}

// getGoFilesInDirectory retrieves all .go files in the given directory and its subdirectories
func getGoFilesInDirectory(directory string) ([]string, error) {
	var goFiles []string

	err := filepath.Walk(directory, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if strings.HasSuffix(info.Name(), ".go") {
			goFiles = append(goFiles, path)
		}
		return nil
	})

	return goFiles, err
}

func checkDbusInGo(directory string) ([]string, error) {
	// Get all .go files in the directory
	filePaths, err := getGoFilesInDirectory(directory)
	if err != nil {
		return nil, fmt.Errorf("error getting .go files: %v", err)
	}

	// Extract method names
	methodNames := extractMethodNamesFromFiles(filePaths)

	return methodNames, nil
}

func astDbusCreate(dir string, dbusMethodResult []string) error {
	fset := token.NewFileSet()
	callGraph := &CallGraph{
		Functions: make(map[string]*ast.FuncDecl),
		Calls:     make(map[string][]string),
		FileSet:   fset,
	}

	err := filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}
		if !info.IsDir() && filepath.Ext(path) == ".go" {
			node, err := parser.ParseFile(fset, path, nil, parser.AllErrors)
			if err != nil {
				log.Println(err)
				return nil
			}
			ast.Inspect(node, func(n ast.Node) bool {
				if funcDecl, ok := n.(*ast.FuncDecl); ok {
					funcName := funcDecl.Name.Name
					callGraph.Functions[funcName] = funcDecl
					ast.Inspect(funcDecl.Body, func(n ast.Node) bool {
						if callExpr, ok := n.(*ast.CallExpr); ok {
							if selExpr, ok := callExpr.Fun.(*ast.SelectorExpr); ok {
								if ident, ok := selExpr.X.(*ast.Ident); ok {
									callGraph.Calls[funcName] = append(callGraph.Calls[funcName], ident.Name)
								}
							} else if ident, ok := callExpr.Fun.(*ast.Ident); ok {
								callGraph.Calls[funcName] = append(callGraph.Calls[funcName], ident.Name)
							}
						}
						return true
					})
				}
				return true
			})
		}
		return nil
	})

	if err != nil {
		return fmt.Errorf("error walking the path %v", err)
	}

	result := Result{
		ProjectPath:     dir,
		DBusMethodCount: len(dbusMethodResult),
		UnsafeCallCount: 0,
		Details:         []UnsafeCallInfo{},
	}

	for _, method := range dbusMethodResult {
		if _, exists := callGraph.Functions[method]; exists {
			checkRiskyCalls(callGraph, method, map[string]bool{}, callGraph.FileSet, method, &result)
		}
	}

	if result.UnsafeCallCount == 0 {
		result.ScanResult = "passed"
	} else {
		result.ScanResult = "unpassed"
	}
	
	// 最后将结果输出为 JSON
	jsonResult, err := json.MarshalIndent(result, "", "    ")
	if err != nil {
		return fmt.Errorf("error marshaling JSON: %v", err)
	}
	fmt.Println(string(jsonResult))

	return nil
}

func readLineFromFile(filename string, lineNumber int) string {
	file, err := os.Open(filename)
	if err != nil {
		log.Printf("无法打开文件: %v", err)
		return ""
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	currentLine := 1
	for scanner.Scan() {
		if currentLine == lineNumber {
			return strings.TrimSpace(scanner.Text())
		}
		currentLine++
	}
	if err := scanner.Err(); err != nil {
		log.Printf("读取文件时出错: %v", err)
	}
	return ""
}

func checkRiskyCalls(callGraph *CallGraph, funcName string, visited map[string]bool, fset *token.FileSet, topFunc string, result *Result) {
	if visited[funcName] {
		return
	}
	visited[funcName] = true

	if funcDecl, exists := callGraph.Functions[funcName]; exists {
		ast.Inspect(funcDecl, func(n ast.Node) bool {
			if callExpr, ok := n.(*ast.CallExpr); ok {
				if selExpr, ok := callExpr.Fun.(*ast.SelectorExpr); ok {
					if pkgIdent, ok := selExpr.X.(*ast.Ident); ok {
						if (pkgIdent.Name == "os" && selExpr.Sel.Name == "Command") ||
							(pkgIdent.Name == "exec" && selExpr.Sel.Name == "Command") ||
							(pkgIdent.Name == "os" && selExpr.Sel.Name == "Run") {
							pos := fset.Position(callExpr.Pos())
							lineContext := readLineFromFile(pos.Filename, pos.Line)

							// 添加详细结果
							result.Details = append(result.Details, UnsafeCallInfo{
								InterfaceName: topFunc,
								FunctionName:  funcName,
								Parameters:    getParameters(funcDecl), // 假设有getParameters函数来获取参数
								UnsafeCall:    pkgIdent.Name + "." + selExpr.Sel.Name,
								CodeLine:      pos.Line,
								FilePath:      pos.Filename,
								CodeContent:   lineContext,
							})

							// 增加不安全调用数
							result.UnsafeCallCount++
							return false
						}
					}
				}
			}
			return true
		})

		// 递归检查调用的函数
		for _, callee := range callGraph.Calls[funcName] {
			checkRiskyCalls(callGraph, callee, visited, fset, topFunc, result)
		}
	}
}

func getParameters(funcDecl *ast.FuncDecl) []string {
	var params []string
	for _, param := range funcDecl.Type.Params.List {
		for _, name := range param.Names {
			params = append(params, name.Name)
		}
	}
	return params
}

func main() {
	// Define the command-line flag for the directory
	dir := flag.String("dir", ".", "Directory to check for .go files")
	flag.Parse()

	// Check if the directory exists
	info, err := os.Stat(*dir)
	if os.IsNotExist(err) {
		fmt.Printf("Directory %s does not exist\n", *dir)
		return
	}

	if !info.IsDir() {
		fmt.Printf("%s is not a directory\n", *dir)
		return
	}
	// 首先进行DBus接口方法提取
	methodResult, err := checkDbusInGo(*dir)
	if err != nil {
		fmt.Printf("Error checking DBus in Go: %v\n", err)
		return
	}

	// 然后进行AST分析并输出结果
	err = astDbusCreate(*dir, methodResult)
	if err != nil {
		fmt.Printf("Error running AST Dbus Create: %v\n", err)
	}
}
