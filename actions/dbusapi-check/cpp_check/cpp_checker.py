import os
import clang.cindex
import utils
import json
import subprocess
import shutil

from utils import XML_PATH, CPP_UNSAFE_CONF_PATH
from log_module import info_log, warning_log, error_log
from collections import defaultdict

llvm7_config = shutil.which("llvm-config-7")
llvm7_lib_path = "/usr/lib/llvm-7/lib"

if llvm7_config:
    clang.cindex.Config.set_library_file("{llvm7_lib_path}/libclang.so")
else:
    # 如果没有找到 llvm-7，获取最新的 LLVM 版本
    llvm_libdir_output = subprocess.check_output(['llvm-config', '--libdir']).decode().strip()
    # 设置最新的库路径
    clang.cindex.Config.set_library_file("{llvm_libdir_output}/libclang.so.1")

# 获取interfaces和methods映射关系
interface_list = utils.parse_dbus_xml(XML_PATH)

# 获取dbus所有的接口的方法
target_methods = []
for methods in interface_list.values():
    target_methods.extend(methods)

# 加载不安全函数列表
unsafe_functions = utils.load_list_from_text(CPP_UNSAFE_CONF_PATH)

# 遍历项目目录，找到所有C++的源文件和头文件
def get_cpp_files(project_path):
    cpp_files = []
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if d != 'include']
        for file in files:
            if file.endswith(('.cpp', '.h', '.hpp', '.cc')):
                cpp_files.append(os.path.join(root, file))
    return cpp_files

# 获取函数具体代码
def get_function_code(cursor):
    try:
        start = cursor.extent.start
        end = cursor.extent.end
        
        with open(cursor.location.file.name, 'r') as f:
            lines = f.readlines()
        
        return ''.join(lines[start.line-1:end.line])
    except FileNotFoundError:
        return f"Error: File '{cursor.location.file.name}' not found."
    except AttributeError as e:
        return f"Error: Invalid cursor object. {e}"
    except IndexError as e:
        return f"Error: Index out of range. {e}"
    except Exception as e:
        return f"Unexpected error: {e}"

def find_dbus_methods(cpp_files):
    tree_structure = defaultdict(lambda: defaultdict(lambda: {"args": [], "dangerous_calls": []}))
    index = clang.cindex.Index.create()

    for file in cpp_files:
        translation_unit = index.parse(file)
        for cursor in translation_unit.cursor.walk_preorder():
            if cursor.kind == clang.cindex.CursorKind.CXX_METHOD:
                if cursor.spelling in target_methods:
                    interface_name = None
                    for iface, methods in interface_list.items():
                        if cursor.spelling in methods:
                            interface_name = iface
                            break

                    if interface_name is None:
                        continue

                    method_name = cursor.spelling
                    params = [param.spelling for param in cursor.get_arguments()]
                    tree_structure[interface_name][method_name]["args"] = params

                    function_code = get_function_code(cursor)

                    in_multiline_comment = False
                    recorded_lines = set()  # 用于记录已经记录的危险调用行号
                    for line_num, line in enumerate(function_code.split('\n'), start=cursor.location.line):
                        stripped_line = line.strip()

                        if stripped_line.startswith("/*"):
                            in_multiline_comment = True

                        if in_multiline_comment:
                            if stripped_line.endswith("*/"):
                                in_multiline_comment = False
                            continue

                        if stripped_line.startswith("//"):
                            continue

                        for unsafe_func in unsafe_functions:
                            if unsafe_func in line and not in_multiline_comment:
                                unsafe_call = line.strip()

                                # 使用文件路径和行号来构建唯一标识
                                call_signature = (file, line_num)

                                # 检查是否已经记录过相同行号的危险调用
                                if call_signature in recorded_lines:
                                    continue  # 如果已经记录过，则跳过
                                
                                print(f"{unsafe_call}")

                                dangerous_call_info = {
                                    "unsafe_function": unsafe_func,
                                    "file_path": file,
                                    "code_line": line_num,
                                    "code_content": unsafe_call
                                }
                                tree_structure[interface_name][method_name]["dangerous_calls"].append(dangerous_call_info)
                                
                                # 将新的危险调用记录到set中
                                recorded_lines.add(call_signature)

    return tree_structure


# 将树状结构转换为json格式，并添加统计信息
def convert_to_json_with_stats(tree_structure, project_path):
    total_methods = 0
    dangerous_methods = 0
    dangerous_calls_list = []

    for interface, methods in tree_structure.items():
        for method, details in methods.items():
            total_methods += 1
            if details["dangerous_calls"]:
                dangerous_methods += 1
                for call in details["dangerous_calls"]:
                    call_info = {
                        "interface_name":interface,
                        "function_name": method,
                        "args": details["args"],
                        "unsafe_call": call["unsafe_function"],
                        "code_line": call["code_line"],
                        "file_path": call["file_path"],
                        "code_content": call["code_content"]
                    }
                    dangerous_calls_list.append(call_info)

    unsafe_call_count = sum(len(method_info["dangerous_calls"]) for interface in tree_structure.values() for method_info in interface.values())
    result = {
        "project_path": project_path,
        "dbus_method_count": total_methods,
        "unsafe_call_count": unsafe_call_count,
        "scan_result": "passed" if not unsafe_call_count else "unpassed",
        "details": dangerous_calls_list
    }

    return json.dumps(result, indent=4, ensure_ascii=False)

# 定义一个函数check_dbus_in_cpp, 来调用以上三个函数实现比对功能
def check_dbus_in_cpp(project_path):
    info_log("正在检查DBus方法...")
    try:
        cpp_files = get_cpp_files(project_path)
        tree_structure = find_dbus_methods(cpp_files)
        json_result = convert_to_json_with_stats(tree_structure, project_path)

        # 解析 JSON 数据
        parsed_json = json.loads(json_result)

        info_log(f"项目:{project_path}，扫描完成")

        if not parsed_json["unsafe_call_count"]:
            info_log(f"检查通过! 未发现危险调用")
            return True, parsed_json
        else:
            warning_log("检查不通过！发现不安全调用")
            return True, parsed_json

    except Exception as e:
        error_log(f"检查过程中发生错误：{e}")
        return False, None