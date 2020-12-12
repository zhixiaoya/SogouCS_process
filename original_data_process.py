# -*- coding: utf-8 -*-

'''
该脚本用于将搜狗语料库新闻语料
转化为按照URL作为类别名、
content作为内容的txt文件存储
'''
import os
import re

'''字符数小于这个数目的content将不被保存'''
threh = 30

'''获取原始语料文件夹下文件列表'''


def listdir_get(path, list_name):
    """
    :desc: get data of raw data
    :input: data of dir, list of slice data path
    """
    for file in os.listdir(path):
        file_path = os.path.join(path, file)
        if os.path.isdir(file_path):
            listdir_get(file_path, list_name)
        else:
            list_name.append(file_path)


'''
#修改文件编码为utf-8
from chardet import detect
def code_transfer(list_name):
    for fn in list_name: 
        with open(fn, 'rb+') as fp:
            content = fp.read()
            codeType = detect(content)['encoding']
            content = content.decode(codeType, "ignore").encode("utf8")
            fp.seek(0)
            fp.write(content)
            print(fn, "：已修改为utf8编码")
'''


def processing(list_name):
    '''对每个语料'''
    for path in list_name:
        print(path + '---start---')
        file = open(path, 'rb').read().decode("utf8")

        '''
        正则匹配出url和content
        '''
        patternURL = re.compile(r'<url>(.*?)</url>', re.S)
        patternCtt = re.compile(r'<content>(.*?)</content>', re.S)

        classes = patternURL.findall(file)
        contents = patternCtt.findall(file)

        '''将内容小于30的去除'''
        for i in reversed(range(contents.__len__())):
            # 如果是reversed (len(range(5))),这种索引是按从大到小的顺序排列，
            # 列表不要随便删除，python会自动增补，导致索引变少
            if len(contents[i]) < threh:
                contents.pop(i)
                classes.pop(i)

        '''进一步取出URL作为样本标签'''
        for i in range(classes.__len__()):
            patterClass = re.compile(r'http://(.*?).sohu.com/', re.S)
            classi = patterClass.findall(classes[i])
            classes[i] = classi[0]

        '''按照URL作为类别存储到处理后文件夹'''
        for i in range(len(classes)):
            file = data_original_path + '/processed/' + classes[i] + '.txt'
            with open(file, 'a+', encoding='utf-8')as f:
                f.write(contents[i] + '\n')
        print(path + '---success---')


if __name__ == '__main__':
    print("----tast start----")
    # 原始语料路径
    data_original_path = "SogouCS.reduced"
    # data_original_path = './SogouCS.reduced/'

    # 获取文件路径
    list_name = []
    listdir_get(data_original_path, list_name)

    # 修改编码
    # code_transfer(listname)
    processing(list_name)

    print('----task success----')