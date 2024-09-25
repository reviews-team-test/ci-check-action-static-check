'''
Descripttion: 
version: 
Author: 
Date: 2024-08-20 17:25:27
LastEditors: smile
LastEditTime: 2024-08-30 09:27:23
'''
import json
import subprocess
import os
from utils import GO_FILE_PATH, GO_CHECK_DIR
from log_module import info_log, warning_log

def check_dbus_in_go(path):
    # 编译Go代码
    try:
        output_path = os.path.join(GO_CHECK_DIR, "dbus_method_check")
        compile_process = subprocess.run(
            ["go", "build", "-o", output_path, GO_FILE_PATH],
            check=True,
            capture_output=True,
            text=True
        )
        if compile_process.returncode != 0:
            info_log(f"编译出错:{compile_process.stderr}")
            return "失败"
    except subprocess.CalledProcessError as e:
        info_log(f"编译出错:{e.stderr}")
        return "失败"

    # 运行编译后的二进制文件
    try:
        run_process = subprocess.run(
            [output_path, "-dir", path],
            check=True,
            capture_output=True,
            text=True
        )
        output = run_process.stdout

        # 输出日志
        info_log(f"项目:{path}，扫描完成，结果如下:")

        # 解析JSON结果
        result = json.loads(output)
        unsafe_found = result['unsafe_call_count'] > 0

        if unsafe_found:
            warning_log(f"检查不通过!发现不安全调用")
            return True, result
        else:
            info_log(f"检查通过!未发现不安全调用")
            return True, result
    
    except subprocess.CalledProcessError as e:
        info_log(f"运行出错:{e.stderr}")
        return False
