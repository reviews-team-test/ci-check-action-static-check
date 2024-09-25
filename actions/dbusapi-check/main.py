#!/usr/bin/env python3 

import argparse
import os
import sys
import utils
import json
import time

from c_check import c_checker
from go_check import go_checker
from cpp_check import cpp_checker
from log_module import info_log, error_log

def main():

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='D-Bus 检查.')
    parser.add_argument('--source_directory', type=str, help='源码路径')
    parser.add_argument('--commit_info_str', type=str, help='提交参数')
    
    args = parser.parse_args()
    
    # 获取源码路径
    source_directory = args.source_directory
    commit_info_str = args.commit_info_str
    commit_info = json.loads(commit_info_str)
    
    # 检查源码路径是否存在
    if not os.path.exists(source_directory):
        error_log(f"Error: The directory '{source_directory}' does not exist.")
        sys.exit(1)
    
    language_check_functions = {
        'c': c_checker.check_dbus_in_c,
        'cpp': cpp_checker.check_dbus_in_cpp,
        'go': go_checker.check_dbus_in_go
    }

    # 检测语言类型
    try:
        info_log(f"开始检测...")
        language = utils.detect_language(source_directory)
        info_log(f"检测到项目语言类型为: {language}")
    except Exception as e:
        error_log(f"Error: 语言检测失败: {e}")
        sys.exit(1)
    
    # 根据语言类型调用相应的检查函数
    check_function = language_check_functions.get(language)
    if check_function is None:
        error_log(f"Error: 不支持的语言类型 '{language}'.")
        sys.exit(1)
    
    try:
        results, data = check_function(source_directory)

        result_sum = {
            'dbus_method_count': data['dbus_method_count'],
            'unsafe_call_count': data['unsafe_call_count'],
            'scan_result': data['scan_result']
        }

        if os.path.exists('result.json'):
        # 如果文件存在，删除文件
            os.remove('result.json')

        with open('result.json', 'w') as f:
            f.write(json.dumps(result_sum))

        if results == True:
            info_log(f"检测项目:{commit_info['repo_name']}\n扫描结果:{result_sum}")
            info_log(f"{language.capitalize()} D-Bus 检查完成！")

            # 发送请求到 webhook
            response_data = utils.send_webhook_request(data, commit_info)
            if response_data:
                info_log(f"DBUS扫描结果发送成功!")
            else:
                error_log(f"DBUS扫描结果请求失败!")

            def parse_data(data, commit_info):
                details = data.get('details', [])
                for detail in details:
                    time.sleep(1)
                    response_v2_data = utils.send_webhook_request_v2(detail, commit_info)   
                    if response_v2_data:
                        info_log(f"系统调用结果请求成功! 函数名：{detail['function_name']}")
                    else:
                        error_log("系统调用结果请求失败!")
            
            if data['scan_result'] == "unpassed":
                parse_data(data, commit_info)
                info_log(f"系统调用结果请求完成!")
            else:
                info_log(f"扫描结果通过, 无需发送系统调用结果请求!")

        else:
            info_log(f"{language.capitalize()} D-Bus 检查异常！")
            sys.exit(1)

    except Exception as e:
        error_log(f"Error: 检查过程出现错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
