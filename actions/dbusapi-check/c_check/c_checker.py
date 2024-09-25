import os
import re
import json
import clang.cindex
import utils
import shutil
import subprocess
from utils import C_UNSAFE_CONF_PATH
from log_module import info_log, error_log, warning_log


llvm7_config = shutil.which("llvm-config-7")
llvm7_lib_path = "/usr/lib/llvm-7/lib"

if llvm7_config:
    clang.cindex.Config.set_library_file("{llvm7_lib_path}/libclang.so")
else:
    # 如果没有找到 llvm-7，获取最新的 LLVM 版本
    llvm_libdir_output = subprocess.check_output(['llvm-config', '--libdir']).decode().strip()
    # 设置最新的库路径
    clang.cindex.Config.set_library_file("{llvm_libdir_output}/libclang.so.1")


def find_sd_bus_methods(source_dir):
    sd_bus_methods = []
    pattern = re.compile(r'SD_BUS_METHOD\([^,]+, [^,]+, [^,]+, (\w+),')
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(('.c', '.h')):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        matches = pattern.findall(content)
                        sd_bus_methods.extend(matches)
                except Exception as e:
                    info_log(f"Error reading file {file_path}: {e}")
                         
    return sd_bus_methods

def analyze_ast_for_functions_with_system_calls(source_dir, sd_bus_methods):
    index = clang.cindex.Index.create()
    found_dangerous_calls = False
    dangerous_call_count = 0
    output_list = []

    def traverse_ast(node, sd_bus_methods, source_file):
        nonlocal found_dangerous_calls
        if node.kind == clang.cindex.CursorKind.FUNCTION_DECL and node.spelling in sd_bus_methods:
            for child in node.get_children():
                traverse_child(child, node.spelling, source_file)
        
        for child in node.get_children():
            traverse_ast(child, sd_bus_methods, source_file)

    def traverse_child(node, func_name, source_file):
        unsafe_functions = utils.load_list_from_text(C_UNSAFE_CONF_PATH)
        nonlocal found_dangerous_calls, dangerous_call_count
        if node.kind == clang.cindex.CursorKind.CALL_EXPR  and node.spelling in unsafe_functions:
            line = node.location.line
            code_line = node.get_definition().extent.start.line if node.get_definition() else line
            file_path = source_file
            code_content = get_code_content(file_path, line)
            if code_content is not None:
                print({code_content})
                # 保存到输出列表中
                output_list.append({
                    "function_name": func_name,
                    "unsafe_call": node.spelling,
                    "code_line": line,
                    "file_path": file_path,
                    "code_content": code_content
                })

                found_dangerous_calls = True
                dangerous_call_count += 1
        
        for child in node.get_children():
            traverse_child(child, func_name, source_file)

    def get_code_content(file_path, line_number):
        """ Helper function to get the code content at a specific line. """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                if 0 < line_number <= len(lines):
                    line_content = lines[line_number - 1].strip()
                    filtered_content = re.sub(r'system\(["\'][^"\']*["\']\)', '', line_content)

                    if "system" in filtered_content:
                        return line_content  # 返回原始行内容，因为它可能包含变量
                    else:
                        return None
                else:
                    return "Line not available"

        except Exception as e:
            return f"Error reading file: {e}"

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(('.c', '.h')):
                source_file = os.path.join(root, file)
                try:
                    args = ['-I/usr/include', '-I/usr/local/include']  # Adjust as needed
                    translation_unit = index.parse(source_file, args=args)
                    traverse_ast(translation_unit.cursor, sd_bus_methods, source_file)
                except clang.cindex.TranslationUnitLoadError as e:
                    error_log(f"Error parsing file {source_file}: {e}")
                except Exception as e:
                    error_log(f"Unexpected error while parsing file {source_file}: {e}")
        
    return found_dangerous_calls, dangerous_call_count, output_list

def check_dbus_in_c(source_dir):
    try:
        sd_bus_methods = find_sd_bus_methods(source_dir)
        info_log(f"项目:{source_dir}，扫描完成，结果如下:")
        found_dangerous_calls, dangerous_call_count, output_list = analyze_ast_for_functions_with_system_calls(source_dir, sd_bus_methods)
    
        result_data = {
            "project_path": source_dir,
            "dbus_method_count": len(sd_bus_methods),
            "unsafe_call_count": dangerous_call_count,
            "scan_result": "passed" if not dangerous_call_count else "unpassed",
            "details": output_list
        }

        if found_dangerous_calls:
            warning_log(f"检查不通过!发现不安全调用")
            return True, result_data
        else:
            info_log(f"检查通过!未发现不安全调用")
            return True, result_data
        
    except Exception as e:
        error_log(f"An error occurred during DBus method checking: {e}")
        return False
