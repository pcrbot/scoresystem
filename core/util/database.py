import os
import time
import traceback
from datetime import datetime

import peewee

from hoshino import logger

class RetryOperationalError(object):
	def execute_sql(self, sql, params=None, commit=True):
		try:
			cursor = super(RetryOperationalError, self).execute_sql(
				sql, params, commit)
		except peewee.OperationalError:
			if not self.is_closed():
				self.close()
			with peewee.__exception_wrapper__:
				cursor = self.cursor()
				cursor.execute(sql, params or ())
				if commit and not self.in_transaction():
					self.commit()
		return cursor
class RetryMySQLDatabase(RetryOperationalError, peewee.MySQLDatabase):
    pass

try:
	from hoshino.config.__bot__ import (MySQL_host, MySQL_password, MySQL_port,
	                                    MySQL_username)
except ImportError:
	from hoshino.config.database import (MySQL_host, MySQL_password, MySQL_port,
	                                     MySQL_username, MySQL_database)

from hoshino.config.database import (TESTING_MODE, get_database,
                                     database_mode, Database_path)

# Define Database Basics

sqlite_filename = Database_path or os.path.expanduser(
	'~/.hoshino/uniform_score.db')


def database(class_name):
	return \
		RetryMySQLDatabase(
			host=MySQL_host,
			port=MySQL_port,
			user=MySQL_username,
			password=MySQL_password,
			database=get_database(class_name),
			charset='utf8',
			autocommit=True
		) if database_mode == 'mysql' else peewee.SqliteDatabase(
			database=sqlite_filename,
			pragmas={
				'journal_mode': 'wal',
				'cache_size': -1024 * 64,
			})

class BaseDatabase(peewee.Model):
	pass


# Define Database Structure
# 如果你要自己添加数据库的定义，请直接继承BaseDatabase类即可，如:
#   class example(BaseDatabase):
#       pass


class score_data(BaseDatabase):
	"""
    积分数据表
    uid:用户的QQ号(bigint)
    score:用户的积分(Decimal,20,2,自动进位)
    """
	uid = peewee.BigIntegerField(primary_key=True)
	score = peewee.DecimalField(max_digits=20, decimal_places=2, auto_round=True, default=0)


class score_log(BaseDatabase):
	"""
    积分变动日志表
    target_uid:积分变动的用户QQ号(bigint)
    operator_uid:操作者QQ号(bigint)
    type:类型，0指代增加，1指代减少(int)
    exchange_score:变动数额(Decimal,20,2,自动进位)
    reason:变动理由(varchar)
    time_created:变动时间(bigint)
    """
	target_uid = peewee.BigIntegerField()
	operator_uid = peewee.BigIntegerField()
	type = peewee.IntegerField()
	exchange_score = peewee.DecimalField(max_digits=20, decimal_places=2, auto_round=True, default=0)
	reason = peewee.CharField(default='')
	time_created = peewee.TimestampField(default=time.time())


# Define Exception Class

class DataBaseException(IOError):
	def __init__(self, database, error=None):
		self.database = database
		self.error = error
	
	def __str__(self):
		return "Error <{}> occurred when attempt to operate database <{}>".format(repr(self.error), repr(self.database))


class NotEnoughScoreError(ValueError):
	def __init__(self, need_score, now_score):
		self.need_score = need_score
		self.now_score = now_score
	
	def __str__(self):
		return "Operation need {} score, but you have {} score" \
			.format(repr(self.need_score), repr(self.now_score))


class ScoreLimitExceededError(ValueError):
	def __init__(self, score_limit, score_type):
		"""
        score_type : 0:`spend` , 1:`get` (int)
        """
		self.score_limit = score_limit
		self.score_type = 'spend' if score_type == 0 else 'get'
	
	def __str__(self):
		return "Operation {} score reached score limit({} score), please retry later." \
			.format(repr(self.score_type), repr(self.score_limit))


# Initialize Database

def init():
	logger.info(f'Initializing Database...')
	if TESTING_MODE:
		logger.warning("PAY ATTENTION!NOW UNDER TESTING MODE!")
	for db in BaseDatabase.__subclasses__():
		try:
			db_name = db.__name__
			db.bind(database(db_name))
			database(db_name).connect()
			if not db.table_exists():
				database(db_name).create_tables([db])
				logger.info(f'Table <{db_name}> not exists, will be created in database <{get_database(db_name)}>.')
			database(db_name).close()
		except Exception as e:
			traceback.print_exc()
			logger.critical(f'Error <{e}> encountered while initializing database <{get_database(db_name)}>.')


init()
