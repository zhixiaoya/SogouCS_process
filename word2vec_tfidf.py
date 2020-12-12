
from pyspark.sql import SparkSession

spark = SparkSession \
    .builder \
    .appName("test1") \
    .config("spark.some.config.option", "some-value") \
    .getOrCreate()
spark.sparkContext.setLogLevel('WARN')


# ���ķִ�
def segmentation(partition):
    import os
    import re
    import jieba
    import jieba.analyse
    import jieba.posseg as pseg
    import codecs

    # abspath = "words"

    # # ��ͼ����û��ʵ�
    # userDict_path = os.path.join(abspath, "ITKeywords.txt")
    # jieba.load_userdict(userDict_path)
    #
    # # ͣ�ô��ı�
    # stopwords_path = os.path.join(abspath, "stopwords.txt")
    # def get_stopwords_list():
    #     """����stopwords�б�"""
    #     stopwords_list = [i.strip() for i in codecs.open(stopwords_path).readlines()]
    #     return stopwords_list
    # # ���е�ͣ�ô��б�
    # stopwords_list = get_stopwords_list()

    # �ִ�
    def cut_sentence(sentence):
        """���и�֮��Ĵ�����й��ˣ�ȥ��ͣ�ôʣ��������ʣ�Ӣ�ĺ��Զ���ʿ��еĴʣ����ȴ���2�Ĵ�"""
        seg_list = pseg.lcut(sentence)
        # seg_list = [i for i in seg_list if i.flag not in stopwords_list]
        filtered_words_list = []
        for seg in seg_list:
            if len(seg.word) <= 1:
                continue
            elif seg.flag == "eng":
                if len(seg.word) <= 2:
                    continue
                else:
                    filtered_words_list.append(seg.word)
            elif seg.flag.startswith("n"):
                filtered_words_list.append(seg.word)
            elif seg.flag in ["x", "eng"]:  # ���Զ�һ�����������Ӣ�ĵ���
                filtered_words_list.append(seg.word)
        return filtered_words_list

    for row in partition:
        if row[1] == '4':
            sentence = re.sub("<.*?>", "", row[4])  # �滻����ǩ����
            words = cut_sentence(sentence)
            yield row[0], row[1], words


# һ����ȡ�ִ�����
# ���ݣ�article_id,channel_id,channel_name,title,content,sentence
article_data = spark.sparkContext.textFile(r'news_data')
article_data = article_data.map(lambda line: line.split('\x01'))
print("ԭʼ����", article_data.take(10))
words_df = article_data.mapPartitions(segmentation).toDF(['article_id', 'channel_id', 'words'])
print("�ִ�����", words_df.take(10))


# ����word2vecѵ���ִ�����
from pyspark.ml.feature import Word2Vec

w2v_model = Word2Vec(vectorSize=100, inputCol='words', outputCol='vector', minCount=3)
model = w2v_model.fit(words_df)
model.write().overwrite().save("models/word2vec_model/python.word2vec")

from pyspark.ml.feature import Word2VecModel

w2v_model = Word2VecModel.load("models/word2vec_model/python.word2vec")
vectors = w2v_model.getVectors()
vectors.show()


# �����ؼ��ʻ�ȡ(tfidf)
# tdidf
# ��Ƶ����tf
from sklearn.feature_extraction.text import CountVectorizer

# vocabSize���ܴʻ�Ĵ�С��minDF���ı��г��ֵ����ٴ���
cv = CountVectorizer(inputCol="words", outputCol="countFeatures", vocabSize=200 * 10000, minDF=1.0)
# ѵ����Ƶͳ��ģ��
cv_model = cv.fit(words_df)
cv_model.write().overwrite().save("models/CV.model")

from sklearn.feature_extraction.text import CountVectorizerModel

cv_model = CountVectorizerModel.load("models/CV.model")
# �ó���Ƶ�������
cv_result = cv_model.transform(words_df)

# idf
from pyspark.ml.feature import IDF

idf = IDF(inputCol="countFeatures", outputCol="idfFeatures")
idf_model = idf.fit(cv_result)
idf_model.write().overwrite().save("models/IDF.model")

# tf-idf
from pyspark.ml.feature import IDFModel

idf_model = IDFModel.load("models/IDF.model")
tfidf_result = idf_model.transform(cv_result)

# ѡȡǰ20����Ϊ�ؼ���,�˴���Ϊ������
def sort_by_tfidf(partition):
    TOPK = 20
    for row in partition:
        # �ҵ�������IDFֵ����������
        _dict = list(zip(row.idfFeatures.indices, row.idfFeatures.values))
        _dict = sorted(_dict, key=lambda x: x[1], reverse=True)
        result = _dict[:TOPK]
        for word_index, tfidf in result:
            yield row.article_id, row.channel_id, int(word_index), round(float(tfidf), 4)

keywords_by_tfidf = tfidf_result.rdd.mapPartitions(sort_by_tfidf).toDF(["article_id", "channel_id", "index", "weights"])

# �����ؼ���������
keywords_list_with_idf = list(zip(cv_model.vocabulary, idf_model.idf.toArray()))

def append_index(data):
    for index in range(len(data)):
        data[index] = list(data[index])  # ��Ԫ��תΪlist
        data[index].append(index)  # ��������
        data[index][1] = float(data[index][1])

append_index(keywords_list_with_idf)
sc = spark.sparkContext
rdd = sc.parallelize(keywords_list_with_idf)  # ����rdd
idf_keywords = rdd.toDF(["keywords", "idf", "index"])

# ������¹ؼ��ʼ�Ȩ��tfidf
keywords_result = keywords_by_tfidf.join(idf_keywords, idf_keywords.index == keywords_by_tfidf.index).select(
    ["article_id", "channel_id", "keywords", "weights"])
print("�ؼ���Ȩ��", keywords_result.take(10))

# ���¹ؼ����������join
keywords_vector = keywords_result.join(vectors, vectors.word == keywords_result.keywords, 'inner')


# 2.�ؼ���Ȩ�س��Դ�����
def compute_vector(row):
    return row.article_id, row.channel_id, row.keywords, row.weights * row.vector

article_keyword_vectors = keywords_vector.rdd.map(compute_vector).toDF(["article_id", "channel_id", "keywords", "weightingVector"])

# ���� collect_set() ��������һƪ���������йؼ��ʵĴ������ϲ�Ϊһ���б�
article_keyword_vectors.registerTempTable('temptable')
article_keyword_vectors = spark.sql("select article_id, min(channel_id) channel_id, collect_set(weightingVector) vectors from temptable group by article_id")

# 3.����Ȩ������ƽ��ֵ
def compute_avg_vectors(row):
    x = 0
    for i in row.vectors:
        x += i
    # ��ƽ��ֵ
    return row.article_id, row.channel_id, x / len(row.vectors)

article_vector = article_keyword_vectors.rdd.map(compute_avg_vectors).toDF(['article_id', 'channel_id', 'articlevector'])
print("��������vector",article_vector.take(10))