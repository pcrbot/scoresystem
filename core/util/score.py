import time
import traceback
from decimal import Decimal
from typing import List, Tuple

import nonebot
from peewee import PeeweeException

from hoshino.config.score import global_score
from hoshino.util import DailyNumberLimiter
from hoshino.util.database import (DataBaseException, NotEnoughScoreError,
                                   ScoreLimitExceededError, database,
                                   score_data, score_log)

score_get_limiter = DailyNumberLimiter(
	global_score.DAILY_SCORE_GET_LIMIT, module='global_score_get')

score_spend_limiter = DailyNumberLimiter(global_score.DAILY_SCORE_SPEND_LIMIT, module='global_score_spend')


class Score:
	"""
    积分操作类,包括:
    - get_score:获取积分数额
    - check_score:检查积分数额
    - add_score:增加积分(原子操作)
    - spend_score:消费积分(原子操作)
    - give_score:给予积分(原子操作)
    - (异步)score_log:获取积分日志
    - (异步)score_rank:获取本群积分排行
    有返回值时即为成功操作。
    操作失败时会返回以下异常:
    `DataBaseException`:数据库操作异常
    `NotEnoughScoreError`:欲消耗超过自己持有的积分数
    `ScoreLimitExceededError`:超过日获取/消耗积分上限
    `AttributeError`:参数错误
    """
	
	def __init__(self, session):
		"""
        实例化时请传入`ev(CQEvent)` 或 `session(CommandSession)` 或 `uid(int)`。
        """
		if type(session) == (int or str):
			try:
				self.uid = int(session)
			except:
				raise AttributeError(
					'Cannot initialize class,please ensure type of session is CQEvent or CommandSession or int.')
		else:
			try:
				self.uid = session.user_id
			except AttributeError:
				self.uid = session.event.user_id
			except:
				raise AttributeError(
					'Cannot initialize class,please ensure type of session is CQEvent or CommandSession or int.')
		
		self.raw_session = session
	
	def _write_log(self, target_uid: int, exchange_score: Decimal, reason: str = ''):
		try:
			score_log.replace(
				target_uid=target_uid,
				operator_uid=self.uid,
				type=0 if exchange_score > 0 else 1,
				exchange_score=exchange_score,
				reason=reason,
				time_created=time.time()).execute()
		
		except PeeweeException as e:
			raise DataBaseException('score', e)
	
	def get_score(self) -> Decimal:
		"""
        获取积分数额
        参数:无
        返回:积分数量
        """
		try:
			score = score_data.get_or_create(uid=self.uid)
			return round(score[0].score, 2)
		
		except PeeweeException as e:
			raise DataBaseException('score', e)
	
	def check_score(self, score) -> bool:
		"""
        检查积分数额
        检查积分数额是否足以扣除
        参数:欲花费的积分数
        返回:能扣除True,反之False(bool)
        """
		try:
			score = Decimal(score)
			return self.get_score() - score >= 0
		
		except:
			traceback.print_exc()
			return False
	
	def add_score(self, score, reason='') -> Decimal:
		"""
        增加积分
        参数:增加的积分数量,
        返回:操作后的积分数量
        """
		try:
			score = Decimal(score)
			
			if global_score.ENABLE_GET_LIMIT:
				if not score_get_limiter.check(self.uid):
					raise ScoreLimitExceededError(
						global_score.DAILY_SCORE_GET_LIMIT, 1)
			
			score_data.replace(uid=self.uid, score=score_data.get_or_create(uid=self.uid)[0].score + score).execute()
			
			if global_score.ENABLE_GET_LIMIT:
				score_get_limiter.increase(self.uid, score)
			
			self._write_log(self.uid, score, reason)
			
			return score_data.get_or_create(uid=self.uid)[0].score
		
		except PeeweeException as e:
			raise DataBaseException('score', e)
	
	def spend_score(self, score, forcibly=False, reason='') -> Decimal:
		"""
        消费积分
        参数:要减少的积分数,是否强制扣除(不检查积分数)(可选,默认False)
        返回:操作后的积分数量
        """
		try:
			score = Decimal(score)
			
			if (now_score := score_data.get_or_create(uid=self.uid)[0].score) - Decimal(score) < 0:
				if not forcibly:
					raise NotEnoughScoreError(score, now_score)
				else:
					pass
			
			if global_score.ENABLE_SPEND_LIMIT:
				if not score_spend_limiter.check(self.uid):
					raise ScoreLimitExceededError(
						global_score.DAILY_SCORE_SPEND_LIMIT, 0)
			
			score_data.replace(uid=self.uid, score=score_data.get_or_create(uid=self.uid)[0].score - score).execute()
			
			if global_score.ENABLE_SPEND_LIMIT:
				score_spend_limiter.increase(self.uid, score)
			
			self._write_log(self.uid, -score, reason)
			
			return score_data.get_or_create(uid=self.uid)[0].score
		
		except PeeweeException as e:
			raise DataBaseException('score', e)
	
	def give_score(self, score, target_uid: int, forcibly=False) -> Tuple[Decimal, Decimal]:
		"""
        给予积分
        参数:要减少的积分数,接受积分的人的QQ号,是否强制扣除(不检查积分数)(可选,默认False)
        返回:操作后的给予积分的人的积分数量,接受积分的人的积分数量
        """
		try:
			score = Decimal(score)
			
			if (now_score := score_data.get_or_create(uid=self.uid)[0].score) - Decimal(score) < 0:
				if not forcibly:
					raise NotEnoughScoreError(score, now_score)
				else:
					pass
			
			if global_score.ENABLE_GET_LIMIT:
				if not score_get_limiter.check(target_uid):
					raise ScoreLimitExceededError(
						global_score.DAILY_SCORE_GET_LIMIT, 1)
			
			if global_score.ENABLE_SPEND_LIMIT:
				if not score_spend_limiter.check(self.uid):
					raise ScoreLimitExceededError(
						global_score.DAILY_SCORE_SPEND_LIMIT, 0)
			
			with database('score_data').atomic():
				score_data.replace(uid=self.uid, score=score_data.get_or_create(uid=self.uid)[0].score - score).execute()
				score_data.replace(uid=target_uid,
				                   score=score_data.get_or_create(uid=target_uid)[0].score + score).execute()
			
			self._write_log(target_uid, -score, reason='赠送他人金币')
			
			if global_score.ENABLE_SPEND_LIMIT:
				score_spend_limiter.increase(self.uid, score)
			if global_score.ENABLE_GET_LIMIT:
				score_get_limiter.increase(target_uid, score)
			
			return score_data.get_or_create(uid=self.uid)[0].score, score_data.get_or_create(uid=target_uid)[0].score
		
		except PeeweeException as e:
			raise DataBaseException('score', e)
	
	async def score_log(self, limit: int = 5) -> List[dict]:
		"""
		获取积分日志(异步)
		参数:获取的条数(可选,默认5条)
		返回:
		[{'target_uid': ...,
		'operator_uid': ...,
		'type': 'spend' or 'get',
		'exchange_score': ...,
		'reason': ...,
		'time_created': ...},
		{'target_uid': ...,
		'operator_uid': ...,
		...},
		...]
		"""
		try:
			logs = score_log.select().where(score_log.operator_uid == self.uid). \
				order_by(score_log.time_created.desc()).limit(limit)
			return [{'target_uid': log.target_uid,
			         'operator_uid': log.operator_uid,
			         'type': 'spend' if log.type == 1 else 'get',
			         'exchange_score': log.exchange_score,
			         'reason': log.reason,
			         'time_created': log.time_created} for log in logs]
		except score_log.DoesNotExist:
			return []
		except Exception as e:
			raise DataBaseException('score', e)
	
	async def score_rank(self, limit: int = 10) -> List[dict]:
		"""
		获取积分排行(异步)
		参数:获取的条数(可选,默认10条)
		**请注意:必须传入原始session或event才能调用**
		返回:
			[{'uid': ...,
			'score': ...},
			...]
		"""
		try:
			self_id = self.raw_session.self_id
			group_id = self.raw_session.group_id
		except AttributeError:
			self_id = self.raw_session.event.self_id
			group_id = self.raw_session.event.group_id
		except:
			raise AttributeError("In order to call this method,please offer session rather than int.")
		try:
			group_member_list = [i['user_id'] for i in
			                     await nonebot.get_bot().get_group_member_list(group_id=group_id, self_id=self_id)]
			rank = score_data.select().where(score_data.uid.in_(group_member_list)).order_by(
				score_data.score.desc()).limit(limit)
			return [{'uid': i.uid, 'score': i.score} for i in rank]
		except Exception as e:
			raise DataBaseException('score', e)
