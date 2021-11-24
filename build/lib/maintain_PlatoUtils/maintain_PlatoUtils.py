from nebula.graph import ttypes,GraphService
from nebula.ConnectionPool import ConnectionPool
from nebula.Client import GraphClient
import pandas as pd
import numpy as np
import tqdm
import os
import time
import json
import maintain_PlatoUtils
import requests

def wrapNebula2Df(nebulaObj):
    '''将platoDB查询到的对象转为df'''
    # print(nebulaObj.column_names)
    if nebulaObj.column_names is not None:
        columnList = [colItem.decode("utf8") for colItem in nebulaObj.column_names]
    else:
        return pd.DataFrame([])
    dataList = []
    if nebulaObj.rows is not None:
        for rowItem in nebulaObj.rows:
            rowList = []
            for colItem in rowItem.columns:
                if type(colItem.value) == bytes:
                    rowList.append(colItem.value.decode("utf8"))
                else:
                    rowList.append(colItem.value)
            dataList.append(rowList.copy())
    else:
        return pd.DataFrame([])
    return pd.DataFrame(dataList, columns=columnList).drop_duplicates()

def pdPlatoTypeSame(pdSeries,gType):
    '''pd.DataFrame的series的数据类型是否和gType一致'''
    if gType=="string":
        if pdSeries.dtype==object:
            return True
    elif gType=="int":
        if pdSeries.dtype==np.int64:
            return True
    elif gType=="double":
        if pdSeries.dtype==np.float64:
            return True
    return False

def delVertex(gClient,sysIdList,delRel=True):
    '''（关联）删除节点'''
    if delRel==True:
        relDf=wrapNebula2Df(gClient.execute_query("SHOW EDGES"))["Name"]
        relList=relDf.values.flatten().tolist()
        for relItem in relList:
            for srcSysIdItem in sysIdList:
                relTailSysIdDf=wrapNebula2Df(gClient.execute_query("GO FROM {srcSysId} OVER {edgeName} BIDIRECT YIELD {edgeName}._dst AS tgtSysId".format(
                    srcSysId=srcSysIdItem,
                    edgeName=relItem)))
                if relTailSysIdDf.shape[0]>0:
                    relTailSysIdList=relTailSysIdDf["tgtSysId"].values.flatten().tolist()
                    delOrderGroupStr=",".join(["{}->{}".format(srcSysIdItem,tailSysIdItem) for tailSysIdItem in relTailSysIdList])
                    delReverseGroupStr=",".join(["{}->{}".format(tailSysIdItem,srcSysIdItem) for tailSysIdItem in relTailSysIdList])
                    delGroupStr=",".join([delOrderGroupStr,delReverseGroupStr])
                    gClient.execute_query("DELETE EDGE {} {}".format(relItem,delGroupStr))
    for batchI in range(0,len(sysIdList),50): 
        delVerGroupStr=",".join([str(sysIdItem) for sysIdItem in sysIdList[batchI:batchI+50]])
        delReq=gClient.execute_query("DELETE VERTEX {}".format(delVerGroupStr))
    return delReq
                
def existTag(nodeType,nodeIdAttr,nodeName,gClient):
    '''查看nodeType的nodeIdAttr为nodeName的节点是否在gClient中（gClient提前设定好图数据库）'''
    searchTagDf=wrapNebula2Df(gClient.execute_query("LOOKUP ON {nodeType} WHERE {nodeType}.{nodeIdAttr}=='{nodeName}'|LIMIT 1".format(
        nodeType=nodeType,
        nodeIdAttr=nodeIdAttr,
        nodeName=nodeName
    )))
    if searchTagDf.shape[0]>0:
        return True
    return False

def transferBetweenPlato(srcGHost,srcGPort,srcGUser,srcGPassword,srcGdbName,
                         tgtGHost,tgtGPort,tgtGUser,tgtGPassword,tgtGdbName,edgeTypeList=[],
                         srcVertexKeynameDict={"srcNodeType":"srcNodeIdAttr"},csv2platoDTypeDict={"srcNodeIdAttr":"string"},
                         batchSize=64,projectName="",platoIP="",platoPort=8083):
    
    srcConnection_pool = ConnectionPool(srcGHost, srcGPort,network_timeout=300000)
    srcClient = GraphClient(srcConnection_pool)
    srcClient.authenticate(srcGUser, srcGPassword)
    srcClient.execute_query("use {}".format(srcGdbName))

    tgtConnection_pool = ConnectionPool(tgtGHost, tgtGPort,network_timeout=300000)
    tgtClient = GraphClient(tgtConnection_pool)
    tgtClient.authenticate(tgtGUser, tgtGPassword)
    tgtClient.execute_query("use {}".format(tgtGdbName))

    # 1.构建data的项目

    # 获取schema
    srcVertexTypeDf=wrapNebula2Df(srcClient.execute_query("SHOW TAGS"))
    srcVertexTypeAttrSetDict={}
    for srcVertexTypeItem in srcVertexTypeDf["Name"].values.tolist():
        tagTypeListStr="DESCRIBE TAG {}".format(srcVertexTypeItem)
        srcVertexInfoDf=wrapNebula2Df(srcClient.execute_query(tagTypeListStr))
        srcVertexTypeAttrSetDict[srcVertexTypeItem]=dict(srcVertexInfoDf.loc[:,["Field","Type"]].values.tolist())
    
    srcEdgeTypeDf=wrapNebula2Df(srcClient.execute_query("SHOW EDGES"))
    srcEdgeTypeAttrSetDict={}
    for srcEdgeTypeItem in srcEdgeTypeDf["Name"].values.tolist():
        if len(edgeTypeList)==0 or srcEdgeTypeItem in edgeTypeList:
            edgeTypeListStr="DESCRIBE EDGE {}".format(srcEdgeTypeItem)
            srcEdgeInfoDf=wrapNebula2Df(srcClient.execute_query(edgeTypeListStr))
            srcEdgeTypeAttrSetDict[srcEdgeTypeItem]=dict(srcEdgeInfoDf.loc[:,["Field","Type"]].values.tolist())
    
    # 构建schema
    for srcVertexTypeAttrSetItem in srcVertexTypeAttrSetDict:
        srcVertexTypeSet=srcVertexTypeAttrSetDict[srcVertexTypeAttrSetItem]
        tagAttrStr=",".join(["{} {}".format(srcVertexTypeItem,srcVertexTypeSet[srcVertexTypeItem] if srcVertexTypeSet[srcVertexTypeItem] not in ["int","double"] else srcVertexTypeSet[srcVertexTypeItem]+" DEFAULT 0") for srcVertexTypeItem in srcVertexTypeSet])
        buildTagSchemaStr="CREATE TAG IF NOT EXISTS {}({}) ".format(srcVertexTypeAttrSetItem,tagAttrStr)
        tgtClient.execute_query(buildTagSchemaStr)

    
    for srcEdgeTypeAttrSetItem in srcEdgeTypeAttrSetDict:
        srcEdgeTypeSet=srcEdgeTypeAttrSetDict[srcEdgeTypeAttrSetItem]
        tagAttrStr=",".join(["{} {}".format(srcEdgeTypeItem,srcEdgeTypeSet[srcEdgeTypeItem]) for srcEdgeTypeItem in srcEdgeTypeSet])
        buildEdgeSchemaStr="CREATE EDGE IF NOT EXISTS {}({}) ".format(srcEdgeTypeAttrSetItem,tagAttrStr)
        tgtClient.execute_query(buildEdgeSchemaStr)

    # 构建index
    for vertexTypeItem in srcVertexKeynameDict:
        tagIndexName="{}_{}_index".format(vertexTypeItem.lower(),srcVertexKeynameDict[vertexTypeItem].lower())
        tgtClient.execute_query("CREATE TAG INDEX IF NOT EXISTS {} ON {}({})".format(tagIndexName,vertexTypeItem,srcVertexKeynameDict[vertexTypeItem]))
        tgtClient.execute_query("REBUILD TAG INDEX {} OFFLINE".format(tagIndexName))

    # 获取nebula graph导入形式的数据
    if len(projectName)==0:
        projectName="tmpProject_{}".format(int(time.time()*1000))
    if "csv2plato" not in os.listdir("."):
        os.mkdir("csv2plato")
    if projectName not in os.listdir("csv2plato"):
        os.mkdir(os.path.join("data",projectName))
    rawSchemaJson={
        "gDbName":tgtGdbName,
        "coverOldData":True, 
        "vertex":[],
        "edge":[]
    }
    vertexRecordList=[]
    edgeRecordList=[]
    for srcVertexTypeItem in tqdm.tqdm(srcVertexKeynameDict):
        batchI=0
        while True:
            vertexSysIdDf=wrapNebula2Df(srcClient.execute_query("LOOKUP ON {vertexType} WHERE {vertexType}.{attrKeyname}!='不可能的名字'|LIMIT {batchI},{batchSize}".format(
                                                                                                                                                vertexType=srcVertexTypeItem,
                                                                                                                                                attrKeyname=srcVertexKeynameDict[srcVertexTypeItem],
                                                                                                                                                batchI=batchI,
                                                                                                                                                batchSize=batchSize
            )))
            if vertexSysIdDf.shape[0]==0:
                break
            vertexSysIdList=vertexSysIdDf["VertexID"].values.tolist()
            vertexSysIdList=[str(vertexSysIdItem) for vertexSysIdItem in vertexSysIdList]

            vertexInfoDf=wrapNebula2Df(srcClient.execute_query("FETCH PROP ON {} {}".format(srcVertexTypeItem,",".join(vertexSysIdList))))
            while vertexInfoDf.shape[0]==0:
                vertexInfoDf=wrapNebula2Df(srcClient.execute_query("FETCH PROP ON {} {}".format(srcVertexTypeItem,",".join(vertexSysIdList))))
                print("line wrong,check!")
            columnList=list(vertexInfoDf.columns)
            columnRenameDict=dict((colItem,colItem.split(".")[1]) for colItem in columnList if "." in colItem)
            vertexInfoDf.rename(columnRenameDict,axis=1,inplace=True)
            vertexInfoDf.drop("VertexID",axis=1,inplace=True)
            vertexInfoDf["{}SysId".format(srcVertexTypeItem)]=vertexInfoDf["{}".format(srcVertexKeynameDict[srcVertexTypeItem])].apply(lambda row:"{}".format(srcVertexTypeItem)+"_"+row)
            if batchI==0:
                vertexInfoDf.to_csv("data/{}/{}Node-fornew.csv".format(projectName,srcVertexTypeItem),index=None)
            else:
                vertexInfoDf.to_csv("data/{}/{}Node-fornew.csv".format(projectName,srcVertexTypeItem),header=None,index=None,mode="a")
            csv2platoAttrMapDict=dict((colItem,colItem) for colItem in vertexInfoDf.columns)
            csvAttrTypeDict=dict((colItem,csv2platoDTypeDict[vertexInfoDf[colItem].dtype.name]) for colItem in vertexInfoDf.columns)

            if srcVertexTypeItem not in vertexRecordList:
                rawSchemaJson["vertex"].append({
                    "file_name":"{}Node-fornew.csv".format(srcVertexTypeItem),
                    "node_type":srcVertexTypeItem,
                    "id_col":srcVertexKeynameDict[srcVertexTypeItem],
                    "csv2plato_attr_map":csv2platoAttrMapDict,
                    "attr_type_map":csvAttrTypeDict
                })
                vertexRecordList.append(srcVertexTypeItem)

            for srcEdgeTypeItem in srcEdgeTypeAttrSetDict:
                for tgtVertexTypeItem in srcVertexKeynameDict:
                    attrListStr=",".join(["{}.{}".format(srcEdgeTypeItem,edgeItem) for edgeItem in srcEdgeTypeAttrSetDict[srcEdgeTypeItem]])
                    if len(attrListStr)==0:
                        attrListStr=""
                    else:
                        attrListStr=","+attrListStr
                    goDf=wrapNebula2Df(srcClient.execute_query("GO FROM {headSysId} OVER {edge} YIELD $^.{headType}.{headKeyname} AS headId,$$.{tailType}.{tailKeyname} AS tailId{attrList}".format(
                        headSysId=",".join(vertexSysIdList),
                        edge=srcEdgeTypeItem,
                        headType=srcVertexTypeItem,
                        headKeyname=srcVertexKeynameDict[srcVertexTypeItem],
                        tailType=tgtVertexTypeItem,
                        tailKeyname=srcVertexKeynameDict[tgtVertexTypeItem],
                        attrList=attrListStr
                    )))
                    goDf.replace("",np.nan,inplace=True)
                    goDf.dropna(inplace=True)
                    if goDf.shape[0]>0:

                        goDf["headId"]=goDf["headId"].apply(lambda row:"{}_".format(srcVertexTypeItem)+row)
                        goDf["tailId"]=goDf["tailId"].apply(lambda row:"{}_".format(tgtVertexTypeItem)+row)
                        columnRenameDict=dict((colItem,colItem.split(".")[1]) for colItem in goDf.columns if "." in colItem)
                        goDf.rename(columnRenameDict,axis=1,inplace=True)

                        if "{}Rel-fornew.csv".format(srcEdgeTypeItem) not in os.listdir("data/{}/".format(projectName)):
                            goDf.to_csv("data/{}/{}Rel-fornew.csv".format(projectName,srcEdgeTypeItem),index=None)
                        else:
                            goDf.to_csv("data/{}/{}Rel-fornew.csv".format(projectName,srcEdgeTypeItem),index=None,header=None,mode="a")
                        
                        csv2platoAttrMapDict=dict((colItem,colItem) for colItem in goDf.columns if colItem not in ["headId","tailId"])
                        csvAttrTypeDict=dict((colItem,csv2platoDTypeDict[goDf[colItem].dtype.name]) for colItem in goDf.columns if colItem not in ["headId","tailId"])
                        
                        if srcEdgeTypeItem not in edgeRecordList:
                            rawSchemaJson["edge"].append({
                                "file_name":"{}Rel-fornew.csv".format(srcEdgeTypeItem),
                                "edge_type":srcEdgeTypeItem,
                                "src_type":srcVertexTypeItem,
                                "tgt_type":tgtVertexTypeItem,
                                "src_id":"headId",
                                "tgt_id":"tailId",
                                "csv2plato_attr_map":csv2platoAttrMapDict,
                                "attr_type_map":csvAttrTypeDict
                            })
                            edgeRecordList.append(srcEdgeTypeItem)

            batchI+=batchSize

    with open("data/{}/rawSchema.json".format(projectName),"w+",encoding="utf8") as rawSchemaJsonFile:
        json.dump(rawSchemaJson,rawSchemaJsonFile)

    fileList=[]
    for fileItem in tqdm.tqdm(os.listdir("csv2plato/"+projectName)):
        if fileItem.split(".")[1]=="csv":
            fileList.append(("csv",(fileItem,open("csv2plato/"+projectName+"/"+fileItem,'rb'),"test/csv")))
        if fileItem.split(".")[1]=="json":
            fileList.append(("json",(fileItem,open("csv2plato/"+projectName+"/"+fileItem,'rb'),"application/json")))

    fileServerUrl="HTTP://{}:{}/csv2platodb/upload".format(platoIP,platoPort)
    response = requests.request("POST", fileServerUrl, files=fileList)
        
    print("finished !")