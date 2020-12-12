#-*- coding:utf-8 -*-
import os
from chardet import detect

data_original_path = "/SogouCS.reduced"

'''生成原始语料文件夹下文件列表'''
def listdir(path, list_name):
    """
    :desc: get data of raw data
    :input: data of dir, list of slice data path
    """
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            listdir(file_path, list_name)
        else:
            list_name.append(file_path)

'''获取所有语料'''
list_name = []

listdir('SogouCS.reduced',list_name)
print(list_name)
for fn in list_name:
    with open(fn, 'rb+') as fp:
        content = fp.read()
        codeType = detect(content)['encoding']
        content = content.decode(codeType, "ignore").encode("utf8")
        fp.seek(0)
        fp.write(content)
        print(fn, "：已修改为utf8编码")