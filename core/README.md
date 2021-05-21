# 核心组件
此为核心组件，直接覆盖`hoshino/util`即可。


**积分系统**：  
需要使用

``` python
from hoshino.util.score import Score # 导入核心代码
from hoshino.util.database import NotEnoughScoreError, DataBaseException, ScoreLimitExceededError # 导入三个异常类(可选)
```
导入后按照其中注释和说明调用接口。

此外，`hoshino/config/score.py`作为积分配置文件，请自己配置。
