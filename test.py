
import time
from re import search
import pandas as pd
from maintain_PlatoUtils.maintain_PlatoUtils import wrapNebula2Df,transferBetweenPlato
from nebula.graph import ttypes,GraphService
from nebula.ConnectionPool import ConnectionPool
from nebula.Client import GraphClient
import tqdm
import numpy as np
import maintain_PlatoUtils

if __name__=="__main__":
    # # test
    # gHost=""
    # platoAPIPort=7001
    # gPort=13708
    # gUser="root"
    # gPassword="nebula"
    # schemaPath="csv2plato"
    # gSpace="for_kg_search"

    # product
    # gHost=""
    # platoAPIPort=8081
    # gPort=8080
    # gUser="root"
    # gPassword="nebula"
    # schemaPath="csv2plato"
    # gSpace="company_product_field_musklin"

    # gConnection_pool = ConnectionPool(gHost, gPort,network_timeout=300000)
    # gClient = GraphClient(gConnection_pool)
    # gClient.authenticate(gUser, gPassword)
    # gClient.execute_query("USE {}".format(gSpace))

    # start=time.time()
    # a=wrapNebula2Df_single(gClient.execute_query("LOOKUP ON Company WHERE Company.CompanyName!='不可能的名字'|LIMIT 10000|FETCH PROP ON Company $-.VertexID"))
    # end=time.time()
    # print(end-start)

    # start=time.time()
    # a=wrapNebula2Df(gClient.execute_query("LOOKUP ON Company WHERE Company.CompanyName!='不可能的名字'|LIMIT 10000|FETCH PROP ON Company $-.VertexID"),batchSize=64)
    # end=time.time()
    # print(end-start)
    
    # start=time.time()
    # a=wrapNebula2Df_process(gClient.execute_query("LOOKUP ON Company WHERE Company.CompanyName!='不可能的名字'|LIMIT 10000|FETCH PROP ON Company $-.VertexID"))
    # end=time.time()
    # print(end-start)
    
    srcGHost=""
    srcGPort=13708
    srcGUser="root"
    srcGPassword="nebula"
    srcGdbName="company_product_field_musklin"
    srcVertexKeynameDict={
        "Product":"ProductName",
        "Field":"FieldName"
    }
    edgeTypeList=["belongTo"]

    tgtGHost=""
    tgtGPort=13708
    tgtGUser="root"
    tgtGPassword="nebula"
    tgtGdbName="for_kg_search"
    csv2platoDTypeDict={
        "object":"string",
        "float64":"double",
        "int64":"int",
    }
    
    transferBetweenPlato(srcGHost,srcGPort,srcGUser,srcGPassword,srcGdbName,
                         tgtGHost,tgtGPort,tgtGUser,tgtGPassword,tgtGdbName,edgeTypeList=edgeTypeList,
                         srcVertexKeynameDict=srcVertexKeynameDict,csv2platoDTypeDict=csv2platoDTypeDict,
                         batchSize=64,projectName="tryTransfer",platoAPIIP="",platoAPIPort=8083)