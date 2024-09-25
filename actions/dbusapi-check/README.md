<!--
 * @Descripttion: 
 * @version: 
 * @Author: 
 * @Date: 2024-08-20 17:24:55
 * @LastEditors: smile
 * @LastEditTime: 2024-09-05 13:23:38
-->
# ci-dbus_args_check

### 简介
dbus_args_check 是一个用于检查D-Bus参数是否符合规范的Python实现。它能够检查参数的类型、数量和顺序是否正确，并提供详细的错误信息。

### 版本信息
Version:v1.0

### 安装    

安装环境环境依赖：
```bash
sudo apt install clang-7 libclang-dev llvm-7 python3-pip
sudo python3 -m pip install -r clang==${version}
sudo apt install golang
```
tips:安装的clang版本需要和python中的版本保持一致,代码中设置环境变量的时候需要根据实际的路径进行修改。

### 使用方法
```bash
使用方法: python3 main.py [-h] [--source_directory SOURCE_DIRECTORY]
               [--commit_info_str COMMIT_INFO_STR]
optional arguments:
  -h, --help            show this help message and exit
  --source_directory SOURCE_DIRECTORY
                        源码路径
  --commit_info_str COMMIT_INFO_STR
                        提交参数

```

## 详细描述
ci-dbus_args_check 是一个集成到CI流程中的用于检查D-Bus代码中是否存在直接使用system、popen等系统调用操作入参的情况，如果存在此操作，则相当于dbus的入参可以被执行shellcode的注入，会存在极大的影响，导致提权。当前该脚本需要实现对代码进行AST分析，并检查是否存在上述操作。已完成对C/GO/C++的支持。

### 代码结构
```
├── c_check
│   ├── c_checker.py                            # C代码检查器
│   ├── c_unsafe_functions.conf                 # C代码中不安全的函数列表
│   └── __init__.py
├── cpp_check                                   
│   ├── cpp_checker.py                          # C++代码检查器
│   ├── cpp_dbus_xml                            # C++代码中dbus xml文件
│   │   ├── com.deepin.anything.xml
│   │   ├── com.deepin.bootmaker.xml
│   │   ├── com.deepin.diskmanager.xml
│   │   ├── com.deepin.filemanager.daemon.AccessControlManager.xml
│   │   ├── com.deepin.filemanager.daemon.EncryptKeyHelper.xml
│   │   ├── com.deepin.filemanager.daemon.MountControl.xml
│   │   ├── com.deepin.filemanager.daemon.UserShareManager.xml
│   │   ├── com.deepin.logviewer.xml
│   │   ├── org.deepin.DeviceControl.xml
│   │   ├── org.deepin.DeviceInfo.xml
│   │   ├── org.deepin.EventLog1.xml
│   │   └── org.deepin.service.SystemNetwork.xml
│   ├── cpp_unsafe_functions.conf              # C++或者QT不安全的函数列表
│   └── __init__.py
├── go_check
│   ├── dbus_method_check.go                    # go代码检查器
│   ├── go_checker.py                           # go代码驱动脚本
│   └── __init__.py
├── log_module.py                               # 日志模块
├── main.py                                     # 主程序入口
├── README.md                                   # README
├── utils.py                                    # 工具函数
└── __init__.py
```


## 计划
todo list:
1、C++项目的分类处理策略，定义一个枚举的策略类型，来实现读取哪些xml文件 --待定。
2、打印信息的统一，以及告警信息的等级。   --已完成
3、返回值的类型整理。                  --已完成
4、修复误报等情况。                    --已完成
5、增加对CI平台和明道云的对接            --已完成
6、检查数据界面的搭建                   --界面展示已完成
7、增加安全审核流程的明道云的搭建         --通过界面完成每一条数据的审核
8、增加对代码检查的精准匹配的程度         -- 待处理