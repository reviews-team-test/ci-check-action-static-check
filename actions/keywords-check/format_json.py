# 格式化json文件内容

import json
import os
import sys

# 读取json文件并美化json显示
def readJsonFile(filepath):
    if os.path.isfile(filepath):
        with open(filepath, 'r', encoding="utf-8") as fin:
            content = json.load(fin)
        return content
# 处理数据
def getData(content):
    new_content = {}
    for fileName in content:
        fileInfo = content[fileName]
        new_fileInfo = []
        for lineInfo in fileInfo:
            new_lineInfo = {}
            new_lineInfo["line"] = lineInfo["line"]
            new_lineInfo["line_number"] = lineInfo["line_number"]
            new_lineInfo["rule"] = lineInfo["rule"]
            new_lineInfo["reason"] = lineInfo["reason"]
            new_fileInfo.append(new_lineInfo)
        new_content[fileName] = new_fileInfo
    return new_content
# 写json文件
def writeJsonFile(resultInfo, jsonFile):
    with open(jsonFile, 'w+') as fp:
      fp.write(json.dumps(resultInfo, indent=4, ensure_ascii=False))
      
jsonFile = sys.argv[1]
newjsonFile = jsonFile.split('.json')[0] + '_new.json'
data = readJsonFile(jsonFile)
new_data = getData(data)
writeJsonFile(new_data, newjsonFile)
