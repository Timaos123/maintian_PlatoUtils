import os
import tqdm
import json
import pandas as pd
import numpy as np
from nebula.graph import ttypes,GraphService
from nebula.ConnectionPool import ConnectionPool
from nebula.Client import GraphClient
from maintain_PlatoUtils.maintain_PlatoUtils import wrapNebula2Df
import maintain_csv2platodb_A_uploadFile
import maintain_csv2platodb_B_submitSchema
import maintain_csv2platodb_C_import

if __name__=="__main__":
    srcGHost=""
    srcGPort=13708
    srcGUser="root"
    srcGPassword="nebula"
    srcGdbName="company_product_field_musklin"
    srcVertexKeynameDict={
        "Company":"CompanyName",
        "Field":"FieldName"
    }
    edgeTypeList=["belongTo"]

    tgtGHost=""
    tgtGPort=13708
    tgtGUser="root"
    tgtGPassword="nebula"
    tgtGdbName="company_product_field_musklin"
    
    projectName="transform_some_data"

    batchSize=64
    myDfList=[]

    csv2platoDTypeDict={
        "object":"string",
        "float64":"double",
        "int64":"int",
    }


    srcConnection_pool = ConnectionPool(srcGHost, srcGPort,network_timeout=300000)
    srcClient = GraphClient(srcConnection_pool)
    srcClient.authenticate(srcGUser, srcGPassword)
    srcClient.execute_query("use {}".format(srcGdbName))

    tgtConnection_pool = ConnectionPool(tgtGHost, tgtGPort,network_timeout=300000)
    tgtClient = GraphClient(tgtConnection_pool)
    tgtClient.authenticate(tgtGUser, tgtGPassword)
    tgtClient.execute_query("use {}".format(tgtGdbName))

    # # 1.构建data的项目

    # # 获取schema
    # srcVertexTypeDf=wrapNebula2Df(srcClient.execute_query("SHOW TAGS"))
    # srcVertexTypeAttrSetDict={}
    # for srcVertexTypeItem in srcVertexTypeDf["Name"].values.tolist():
    #     tagTypeListStr="DESCRIBE TAG {}".format(srcVertexTypeItem)
    #     srcVertexInfoDf=wrapNebula2Df(srcClient.execute_query(tagTypeListStr))
    #     srcVertexTypeAttrSetDict[srcVertexTypeItem]=dict(srcVertexInfoDf.loc[:,["Field","Type"]].values.tolist())
    
    # srcEdgeTypeDf=wrapNebula2Df(srcClient.execute_query("SHOW EDGES"))
    # srcEdgeTypeAttrSetDict={}
    # for srcEdgeTypeItem in srcEdgeTypeDf["Name"].values.tolist():
    #     if len(edgeTypeList)==0 or srcEdgeTypeItem in edgeTypeList:
    #         edgeTypeListStr="DESCRIBE EDGE {}".format(srcEdgeTypeItem)
    #         srcEdgeInfoDf=wrapNebula2Df(srcClient.execute_query(edgeTypeListStr))
    #         srcEdgeTypeAttrSetDict[srcEdgeTypeItem]=dict(srcEdgeInfoDf.loc[:,["Field","Type"]].values.tolist())
    
    # # 构建schema
    # for srcVertexTypeAttrSetItem in srcVertexTypeAttrSetDict:
    #     srcVertexTypeSet=srcVertexTypeAttrSetDict[srcVertexTypeAttrSetItem]
    #     tagAttrStr=",".join(["{} {}".format(srcVertexTypeItem,srcVertexTypeSet[srcVertexTypeItem] if srcVertexTypeSet[srcVertexTypeItem] not in ["int","double"] else srcVertexTypeSet[srcVertexTypeItem]+" DEFAULT 0") for srcVertexTypeItem in srcVertexTypeSet])
    #     buildTagSchemaStr="CREATE TAG IF NOT EXISTS {}({}) ".format(srcVertexTypeAttrSetItem,tagAttrStr)
    #     tgtClient.execute_query(buildTagSchemaStr)

    
    # for srcEdgeTypeAttrSetItem in srcEdgeTypeAttrSetDict:
    #     srcEdgeTypeSet=srcEdgeTypeAttrSetDict[srcEdgeTypeAttrSetItem]
    #     tagAttrStr=",".join(["{} {}".format(srcEdgeTypeItem,srcEdgeTypeSet[srcEdgeTypeItem]) for srcEdgeTypeItem in srcEdgeTypeSet])
    #     buildEdgeSchemaStr="CREATE EDGE IF NOT EXISTS {}({}) ".format(srcEdgeTypeAttrSetItem,tagAttrStr)
    #     tgtClient.execute_query(buildEdgeSchemaStr)

    # # 构建index
    # for vertexTypeItem in srcVertexKeynameDict:
    #     tagIndexName="{}_{}_index".format(vertexTypeItem.lower(),srcVertexKeynameDict[vertexTypeItem].lower())
    #     tgtClient.execute_query("CREATE TAG INDEX IF NOT EXISTS {} ON {}({})".format(tagIndexName,vertexTypeItem,srcVertexKeynameDict[vertexTypeItem]))
    #     tgtClient.execute_query("REBUILD TAG INDEX {} OFFLINE".format(tagIndexName))

    # # 获取nebula graph导入形式的数据
    # if projectName not in os.listdir("data"):
    #     os.mkdir(os.path.join("data",projectName))
    # rawSchemaJson={
    #     "gDbName":tgtGdbName,
    #     "coverOldData":True, 
    #     "vertex":[],
    #     "edge":[]
    # }
    # vertexRecordList=[]
    # edgeRecordList=[]
    # for srcVertexTypeItem in tqdm.tqdm(srcVertexKeynameDict):
    #     batchI=0
    #     while True:
    #         vertexSysIdDf=wrapNebula2Df(srcClient.execute_query("LOOKUP ON {vertexType} WHERE {vertexType}.{attrKeyname}!='不可能的名字'|LIMIT {batchI},{batchSize}".format(
    #                                                                                                                                             vertexType=srcVertexTypeItem,
    #                                                                                                                                             attrKeyname=srcVertexKeynameDict[srcVertexTypeItem],
    #                                                                                                                                             batchI=batchI,
    #                                                                                                                                             batchSize=batchSize
    #         )))
    #         if vertexSysIdDf.shape[0]==0:
    #             break
    #         vertexSysIdList=vertexSysIdDf["VertexID"].values.tolist()
    #         vertexSysIdList=[str(vertexSysIdItem) for vertexSysIdItem in vertexSysIdList]

    #         vertexInfoDf=wrapNebula2Df(srcClient.execute_query("FETCH PROP ON {} {}".format(srcVertexTypeItem,",".join(vertexSysIdList))))
    #         while vertexInfoDf.shape[0]==0:
    #             vertexInfoDf=wrapNebula2Df(srcClient.execute_query("FETCH PROP ON {} {}".format(srcVertexTypeItem,",".join(vertexSysIdList))))
    #             print("line wrong,check!")
    #         columnList=list(vertexInfoDf.columns)
    #         columnRenameDict=dict((colItem,colItem.split(".")[1]) for colItem in columnList if "." in colItem)
    #         vertexInfoDf.rename(columnRenameDict,axis=1,inplace=True)
    #         vertexInfoDf.drop("VertexID",axis=1,inplace=True)
    #         vertexInfoDf["{}SysId".format(srcVertexTypeItem)]=vertexInfoDf["{}".format(srcVertexKeynameDict[srcVertexTypeItem])].apply(lambda row:"{}".format(srcVertexTypeItem)+"_"+row)
    #         if batchI==0:
    #             vertexInfoDf.to_csv("data/{}/{}Node-fornew.csv".format(projectName,srcVertexTypeItem),index=None)
    #         else:
    #             vertexInfoDf.to_csv("data/{}/{}Node-fornew.csv".format(projectName,srcVertexTypeItem),header=None,index=None,mode="a")
    #         csv2platoAttrMapDict=dict((colItem,colItem) for colItem in vertexInfoDf.columns)
    #         csvAttrTypeDict=dict((colItem,csv2platoDTypeDict[vertexInfoDf[colItem].dtype.name]) for colItem in vertexInfoDf.columns)

    #         if srcVertexTypeItem not in vertexRecordList:
    #             rawSchemaJson["vertex"].append({
    #                 "file_name":"{}Node-fornew.csv".format(srcVertexTypeItem),
    #                 "node_type":srcVertexTypeItem,
    #                 "id_col":srcVertexKeynameDict[srcVertexTypeItem],
    #                 "csv2plato_attr_map":csv2platoAttrMapDict,
    #                 "attr_type_map":csvAttrTypeDict
    #             })
    #             vertexRecordList.append(srcVertexTypeItem)

    #         for srcEdgeTypeItem in srcEdgeTypeAttrSetDict:
    #             for tgtVertexTypeItem in srcVertexKeynameDict:
    #                 attrListStr=",".join(["{}.{}".format(srcEdgeTypeItem,edgeItem) for edgeItem in srcEdgeTypeAttrSetDict[srcEdgeTypeItem]])
    #                 if len(attrListStr)==0:
    #                     attrListStr=""
    #                 else:
    #                     attrListStr=","+attrListStr
    #                 goDf=wrapNebula2Df(srcClient.execute_query("GO FROM {headSysId} OVER {edge} YIELD $^.{headType}.{headKeyname} AS headId,$$.{tailType}.{tailKeyname} AS tailId{attrList}".format(
    #                     headSysId=",".join(vertexSysIdList),
    #                     edge=srcEdgeTypeItem,
    #                     headType=srcVertexTypeItem,
    #                     headKeyname=srcVertexKeynameDict[srcVertexTypeItem],
    #                     tailType=tgtVertexTypeItem,
    #                     tailKeyname=srcVertexKeynameDict[tgtVertexTypeItem],
    #                     attrList=attrListStr
    #                 )))
    #                 goDf.replace("",np.nan,inplace=True)
    #                 goDf.dropna(inplace=True)
    #                 if goDf.shape[0]>0:

    #                     goDf["headId"]=goDf["headId"].apply(lambda row:"{}_".format(srcVertexTypeItem)+row)
    #                     goDf["tailId"]=goDf["tailId"].apply(lambda row:"{}_".format(tgtVertexTypeItem)+row)
    #                     columnRenameDict=dict((colItem,colItem.split(".")[1]) for colItem in goDf.columns if "." in colItem)
    #                     goDf.rename(columnRenameDict,axis=1,inplace=True)

    #                     if "{}Rel-fornew.csv".format(srcEdgeTypeItem) not in os.listdir("data/{}/".format(projectName)):
    #                         goDf.to_csv("data/{}/{}Rel-fornew.csv".format(projectName,srcEdgeTypeItem),index=None)
    #                     else:
    #                         goDf.to_csv("data/{}/{}Rel-fornew.csv".format(projectName,srcEdgeTypeItem),index=None,header=None,mode="a")
                        
    #                     csv2platoAttrMapDict=dict((colItem,colItem) for colItem in goDf.columns if colItem not in ["headId","tailId"])
    #                     csvAttrTypeDict=dict((colItem,csv2platoDTypeDict[goDf[colItem].dtype.name]) for colItem in goDf.columns if colItem not in ["headId","tailId"])
                        
    #                     if srcEdgeTypeItem not in edgeRecordList:
    #                         rawSchemaJson["edge"].append({
    #                             "file_name":"{}Rel-fornew.csv".format(srcEdgeTypeItem),
    #                             "edge_type":srcEdgeTypeItem,
    #                             "src_type":srcVertexTypeItem,
    #                             "tgt_type":tgtVertexTypeItem,
    #                             "src_id":"headId",
    #                             "tgt_id":"tailId",
    #                             "csv2plato_attr_map":csv2platoAttrMapDict,
    #                             "attr_type_map":csvAttrTypeDict
    #                         })
    #                         edgeRecordList.append(srcEdgeTypeItem)

    #         batchI+=batchSize

    # with open("data/{}/rawSchema.json".format(projectName),"w+",encoding="utf8") as rawSchemaJsonFile:
    #     json.dump(rawSchemaJson,rawSchemaJsonFile)

    # 2.上传至数据库
    # 记得把项目文件从data迁移到csv2platodb

    # with open("envSet.json","r",encoding="utf8") as envSetFile:
    #     env=json.load(envSetFile)["env"]
    env="test"

    seachFrameworkIpDict={
        "test":"http://localhost:8080",
        "product":"http://hr-graph-service:8080"
    }
    seachFrameworkIp=seachFrameworkIpDict[env]

    esHostDict={
        "test":["9.134.92.196",9200,"elastic","devcloud@123"],
        "product":["http://es.hrsdc.oa.com",80,"aicenter","aicenter@123"]
    }
    esHostConf=esHostDict[env]

    gdbHostDict={
        "test":["",13708,"root","nebula"],
        "product":["",8080,"root","nebula"]
    }
    gdbHost=gdbHostDict[env]

    gdbAPIDict={
        "test":"http://:7001",
        "product":"http://:8081"
    }
    gAPIUrl=gdbAPIDict[env]

    logAPIDict={
        "test":"http://demo.ntsgw.oa.com/api/pub/hr-ai-recruit-center/api/general_ai/ai_api_log",
        "product":"http://vpc.ntsgw.oa.com/api/pub/hr-ai-recruit-center/api/general_ai/ai_api_log"
    }
    logLoc=logAPIDict[env]

    projectFolderName="csv2platodb/{}".format(projectName)
    
    maintain_csv2platodb_A_uploadFile.uploadFolder(projectFolderName,gAPIUrl)
    
    with open("csv2platodb/{}/rawSchema.json".format(projectName),"r",encoding="utf8") as rawSchemaJsonFile:
        rawSchemaJson=json.load(rawSchemaJsonFile)
    uploadSchemaJson=maintain_csv2platodb_A_uploadFile.remakeRawSchema(rawSchemaJson,csvFolder="./csv2platodb/"+projectName,gClient=tgtClient)
    with open("csv2platodb/{}/uploadSchema.json".format(projectName),"w",encoding="utf8") as uploadSchemaJsonFile:
        json.dump(uploadSchemaJson,uploadSchemaJsonFile)

    with open(projectFolderName+"/uploadSchema.json","r") as uploadSchemaFile:
        uploadSchemaJson=json.load(uploadSchemaFile)
    gspace=uploadSchemaJson["gDbName"]

    gConnection_pool = ConnectionPool(gdbHost[0], gdbHost[1],network_timeout=300000)
    gClient = GraphClient(gConnection_pool)
    gClient.authenticate(gdbHost[2], gdbHost[3])
    
    maintain_csv2platodb_B_submitSchema.createSchemaFromSchemaJson(uploadSchemaJson,graphClient=gClient)
    gClient.execute_query("USE {}".format(gspace))
    gClient.set_space(gspace)
    
    vertexJsonList=[]
    edgeJsonList=[]
    if "vertex" in uploadSchemaJson:
        vertexJsonList=maintain_csv2platodb_B_submitSchema.buildVertex(uploadSchemaJson["vertex"],graphClient=gClient)
    if "edge" in uploadSchemaJson:
        edgeJsonList=maintain_csv2platodb_B_submitSchema.buildEdge(uploadSchemaJson["edge"],graphClient=gClient)
    
    schemaJson={
        "version": "v1rc1",
        "description": "web console import",
        "clientSettings": {
            "concurrency": 10,
            "channelBufferSize": 128,
            "space": gspace,
            "connection": {
                "user": gdbHost[2],
                "password": gdbHost[3],
                "address": "{}:{}".format(gdbHost[0],gdbHost[1])
            }
        },
        "logPath": "/upload-dir/tmp/import.log",
        "files": vertexJsonList+edgeJsonList
    }
    with open(projectFolderName+"/schemaJson.json","w+") as schemaJsonFile:
        json.dump(schemaJson,schemaJsonFile)
        
    taskId=maintain_csv2platodb_B_submitSchema.submitSchema(schemaJson,gUrl=gAPIUrl)
    maintain_csv2platodb_C_import.importData(gAPIUrl,taskId=taskId)
        
    print("finished !")