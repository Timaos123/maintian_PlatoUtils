from nebula.graph import ttypes,GraphService
from nebula.ConnectionPool import ConnectionPool
from nebula.Client import GraphClient
import pandas as pd
import numpy as np

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
        delVerGroupStr=",".join([str(sysIdItem) for sysIdItem in sysIdList[batchI,batchI+50]])
        delReq=gClient.execute_query("DELETE VERTEX {}".format(delVerGroupStr))
    return delReq
                