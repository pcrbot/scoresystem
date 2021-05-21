# 核心组件
此为核心组件，直接覆盖`hoshino/util`即可。


## 积分系统：  
需要使用

``` python
from hoshino.util.score import Score # 导入核心代码
from hoshino.util.database import NotEnoughScoreError, DataBaseException, ScoreLimitExceededError # 导入三个异常类(可选)
```
导入后按照其中注释和说明调用接口。

### demo

``` python
# 以花费积分和查询积分为例
from hoshino.util.score import Score
from hoshino.util.database import NotEnoughScoreError, DataBaseException, ScoreLimitExceededError 

@sv.on_fullmatch('花点积分')
async def spend_gold(bot, ev):
	gold = Score(ev) 
    # 首先实例化类,可以传入CQEvent和CommandSession,对于定时任务,直接传入uid即可
	try:
		now_gold = gold.spend_score('5') # 花费积分,其他方法见源码
		await bot.send(ev, f'你花掉了5 积分，你现在有{now_gold} 积分')
	except NotEnoughScoreError as e: 
        # 积分不够花
        # 判断积分是否够用还可以使用`check_score`方法,这样就不用处理异常
		await bot.send(
            ev, f'你只有{e.args[1]} 积分，不足以花掉{e.args[0]} 积分')
        # 从异常信息中获取参数(args1:现有积分数,args2:需要花掉的积分数)
	except ScoreLimitExceededError as e: 
        # 积分花太多(没有启用花费上限可以不用处理)
		await bot.send(ev, f'你今天已经花了{e.args[0]} 积分了，请明天再来吧')
	except DataBaseException as e: # 数据库操作失败
		await bot.send(ev, f'花费积分失败(Error:{e})，请联系维护组')

@sv.on_fullmatch('查询积分数')
async def query_gold(bot, ev):
	gold = Score(ev)
	try:
		now_gold = gold.get_score() # 获取积分数
		await bot.send(ev, f'你现在有{now_gold} 积分')
	except DataBaseException as e:
		await bot.send(ev, f'获取积分数目失败(Error:{e})，请联系维护组')
```
