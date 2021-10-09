# maintian_PlatoUtils

安装方式

```
pip install maintainPlatoUtils
python setup.py install --user
```

每次更新包之后记得删除原dist内的老包，再运行：
```
python -m build
twine upload dist/*
```

文件```.pypirc```置于C:/用户/<用户名>下才能使用