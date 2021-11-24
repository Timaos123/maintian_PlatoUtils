import pandas as pd
import json
import os
import requests
import http.client
import mimetypes
from codecs import encode
from maintain_PlatoUtils.maintain_PlatoUtils import existTag

csv2platoDTypeDict={
    "object":"string",
    "float64":"double",
}

def evalDataType(myDf):
    '''
    分析DataFrame的属性的数据类型
    '''
    attrTypeDict=dict(
        (colItem,csv2platoDTypeDict.get(str(myDf[colItem].dtype),colItem))
        for colItem in myDf.columns
    )
    return attrTypeDict

def uploadFolder(dataFolder,platoUrl):
    
    if "uploadSchema.json" in os.listdir(dataFolder):
        
        with open(os.path.join(dataFolder,"uploadSchema.json").replace("\\","/"),"r",encoding="utf8") as uploadSchemaFile:
            uploadSchemaJson=json.load(uploadSchemaFile)
        
        if "vertex" in uploadSchemaJson:
            for vertexTypeItem in uploadSchemaJson["vertex"]:
                filePath=vertexTypeItem["file_path"]
                uploadFile(filePath,platoUrl=platoUrl)
            
        if "edge" in uploadSchemaJson:
            for edgeTypeItem in uploadSchemaJson["edge"]:
                filePath=edgeTypeItem["file_path"]
                uploadFile(filePath,platoUrl=platoUrl)
    
def remakeRawSchema(rawSchemaJson,csvFolder="",gClient=None):
    '''
    数据需要已上传至服务器的data/csv文件夹内才能使用
    将上传至服务器的schema调整为即将上传至图数据库的schema
    同时，data/csv内的节点信息csv文件会增加newMadeSysID列
    schema数据如下：
    {
        "gDbName":"DemoSpace",
        "coverOldData":True,
        "vertex":[
            {
                "file_name":"vertexData.csv",
                "node_type":"vertexClass",
                "id_col":"vertexIDColName",
                "csv2plato_attr_map":{
                    "csvAttr":"platoAttr"
                },
                "attr_type_map":{
                    "csvAttr":"platoAttrType"
                }
            },
            ......
        ],
        "edge":[
            {
                "file_name":"edgeInfo.csv",
                "edge_type":"edgeClass",
                "src_type":"srcClass1",
                "tgt_type":"tgtClass2",
                "src_id":"srcIdAttr",
                "tgt_id":"tgtIdAttr",
            },
            ......
        ]
    }
    '''
    if csvFolder[-1]=="/":
        csvFolder=csvFolder[:-1]
    coverOldData=rawSchemaJson.get("coverOldData",True)
    for vertexI,_ in enumerate(rawSchemaJson["vertex"]):
        rawSchemaJson["vertex"][vertexI]["file_path"]=csvFolder+"/"+rawSchemaJson["vertex"][vertexI]["file_name"]
        csvDfItem=pd.read_csv(rawSchemaJson["vertex"][vertexI]["file_path"])
        vertexType=rawSchemaJson["vertex"][vertexI]["node_type"]
        csvDfItem["newMadeSysID"]=vertexType+"_"+csvDfItem[rawSchemaJson["vertex"][vertexI]["id_col"]].astype(str)
        if coverOldData==False:
            nodeType=rawSchemaJson["vertex"][vertexI]["node_type"]
            nodeIdAttr=rawSchemaJson["vertex"][vertexI]["id_col"]
            csvDfItem=csvDfItem.loc[csvDfItem[rawSchemaJson["vertex"][vertexI]["id_col"]].str.apply(lambda myWord:existTag(nodeType, nodeIdAttr, myWord,gClient))==False,:]
        csvDfItem.to_csv(rawSchemaJson["vertex"][vertexI]["file_path"],index=None)
        rawSchemaJson["vertex"][vertexI]["old_id_col"]=rawSchemaJson["vertex"][vertexI]["id_col"]
        rawSchemaJson["vertex"][vertexI]["id_col"]="newMadeSysID"
        if "csv2plato_attr_map" not in rawSchemaJson["vertex"][vertexI] or len(rawSchemaJson["vertex"][vertexI]["attr_type_map"])==0: # 若没有属性映射则进行同名映射
            vertexItemDf=pd.read_csv(rawSchemaJson["vertex"][vertexI]["file_path"])
            rawSchemaJson["vertex"][vertexI]["csv2plato_attr_map"]=dict((colItem,colItem) for colItem in vertexItemDf.columns)
        if "attr_type_map" not in rawSchemaJson["vertex"][vertexI] or len(rawSchemaJson["vertex"][vertexI]["attr_type_map"])==0: # 若没有属性数据类型约束则自动生成
            vertexItemDf=pd.read_csv(rawSchemaJson["vertex"][vertexI]["file_path"])
            CPAttrTypeDict=evalDataType(vertexItemDf)
            rawSchemaJson["vertex"][vertexI]["attr_type_map"]=CPAttrTypeDict
    for edgeI,_ in enumerate(rawSchemaJson["edge"]):
        rawSchemaJson["edge"][edgeI]["file_path"]=csvFolder+"/"+rawSchemaJson["edge"][edgeI]["file_name"]
        csvDfItem=pd.read_csv(rawSchemaJson["edge"][edgeI]["file_path"])
        srcType=rawSchemaJson["edge"][edgeI]["src_type"]
        tgtType=rawSchemaJson["edge"][edgeI]["tgt_type"]
        csvDfItem[rawSchemaJson["edge"][edgeI]["src_id"]]=csvDfItem[rawSchemaJson["edge"][edgeI]["src_id"]].astype(str).apply(lambda row:srcType+"_"+row if srcType+"_" not in row else row) # 同src的newMadeSysID对应
        csvDfItem[rawSchemaJson["edge"][edgeI]["tgt_id"]]=csvDfItem[rawSchemaJson["edge"][edgeI]["tgt_id"]].astype(str).apply(lambda row:tgtType+"_"+row if tgtType+"_" not in row else row) # 同tgt的newMadeSysID对应
        csvDfItem.to_csv(rawSchemaJson["edge"][edgeI]["file_path"],index=None)
        if "csv2plato_attr_map" not in rawSchemaJson["edge"][edgeI] or len(rawSchemaJson["vertex"][edgeI]["attr_type_map"])==0:
            edgeItemDf=pd.read_csv(rawSchemaJson["edge"][edgeI]["file_path"])
            rawSchemaJson["edge"][edgeI]["csv2plato_attr_map"]=dict((colItem,colItem) for colItem in edgeItemDf.columns)
        if "attr_type_map" not in rawSchemaJson["edge"][edgeI] or len(rawSchemaJson["edge"][edgeI]["attr_type_map"])==0:
            edgeItemDf=pd.read_csv(rawSchemaJson["edge"][edgeI]["file_path"])
            CPAttrTypeDict=evalDataType(edgeItemDf)
            rawSchemaJson["edge"][edgeI]["attr_type_map"]=CPAttrTypeDict
    
    return rawSchemaJson

def uploadFile(filepath,platoUrl="http://:7001"):

    url = platoUrl+"/api/files/upload"

    newFilePath=filepath[:filepath.index(".csv")]+"_copy.csv"
    pd.read_csv(filepath).to_csv(newFilePath,header=None,index=None)
    dataList = []
    boundary = 'wL36Yn8afVp8Ag7AmP8qZ0SA4n1v9T'
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=filename; filename={0}'.format(newFilePath)))

    fileType = mimetypes.guess_type(newFilePath)[0] or 'application/octet-stream'
    dataList.append(encode('Content-Type: {}'.format(fileType)))
    dataList.append(encode(''))

    with open(newFilePath, 'rb') as f:
        dataList.append(f.read())
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=Content-Disposition;'))

    dataList.append(encode('Content-Type: {}'.format('text/plain')))
    dataList.append(encode(''))

    dataList.append(encode("form-data"))
    dataList.append(encode('--' + boundary))
    dataList.append(encode('Content-Disposition: form-data; name=name;'))
    body = b'\r\n'.join(dataList)

    headers = {
        'Proxy-Connection': 'keep-alive',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.62',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': '*/*',
        'Origin': platoUrl,
        'Referer': platoUrl+'/import',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'Cookie': '_ga=GA1.1.152281212.1620638476; _gid=GA1.1.1165891708.1630551473; x-client-ssid=17ba9820824-91dabf2075180054237c14cb90d316c04da7064c; x-host-key-front=17ba982086f-036361ce77df67838d947d8c522a9c2ecc4fe227; x-host-key-ngn=17ba9820824-8f6fc182b3bf107c56e7f4e98120e8d99fecabb3; Hm_lvt_b9cb5b394fd669583c13f8975ca64ff0=1628591085,1629950390,1630551473,1630636476; locale=ZH_CN; nsid=f4a441a23dae744c54b8f96960a04ee2; nh=:8080; nu=root; np=nebula; Hm_lpvt_b9cb5b394fd669583c13f8975ca64ff0=1630636498; _gat_gtag_UA_60523578_4=1',
        'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
    }

    response = requests.request("POST", url, headers=headers, data=body)

    print(response.text)

if __name__=="__main__":
    
    dataFolder="csv2platodb/attr2Vertex_1629250000"
    platoUrl="http://:7001"
    # platoUrl="http://:8081"
    
    uploadFolder(dataFolder,platoUrl)
    
    print("finished")
                