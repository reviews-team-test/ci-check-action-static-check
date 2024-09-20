import xml.etree.ElementTree as ET
import argparse
import os

def cppcheck_del_noterror(file):  # 将原结果xml文件中error部分根据列表文件进行过滤，生成新的结果xml文件
    avalible_suffix = ['.cpp', '.cxx', '.cc', '.c++', '.c', '.ipp', '.ixx', '.tpp', '.txx']
    if os.path.getsize(file) != 0:
        delTree = ET.parse(file)
        root = delTree.getroot()
        for child in root.findall("errors"):
            for fi in child.findall('error'):
                fileName = fi.get('file0')
                if files_lst:
                    if fileName not in files_lst or '.' + fileName.split('.')[1] not in avalible_suffix:
                        child.remove(fi)
        delTree.write(f'{xmlNewName}.xml')  # 生成新的xml文件


def golangcilint_del_noterror(file): # 将原结果xml文件中testsuite部分根据列表文件name进行过滤，生成新的结果xml文件
    failures = 0
    if os.path.getsize(file) != 0:
        delTree = ET.parse(file)
        root = delTree.getroot()
        for child in root.findall("testsuite"):
            fileName = child.get('name')
            if files_lst:
                if fileName not in files_lst or fileName.split('.')[1] != 'go':
                    root.remove(child)
        delTree.write(f'{xmlNewName}.xml')  # 生成新的xml文件
    return failures


if __name__ == '__main__':
    parse = argparse.ArgumentParser(description='cpp result file filter')
    parse.add_argument('--type', help='检查工具类型')
    parse.add_argument('--file', help='cppcheck检查列表文件')
    parse.add_argument('--xml', help='待过滤的源xml文件')
    args = parse.parse_args()
    file = args.file
    source_xml = args.xml
    type = args.type

    files_lst = []
    xmlNewName = source_xml.split('.xml')[0] + '_new'
    if os.path.exists(file):
        with open(file, 'r') as fp:
            for line in fp:
                line = line.strip().strip('\n')[2:]
                files_lst.append(line)
    if type == 'cppcheck':
        cppcheck_del_noterror(source_xml)
    elif type == 'golangci-lint':
        failures = golangcilint_del_noterror(source_xml)
        print(failures)