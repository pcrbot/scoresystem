database_mode = '' # 数据库模式:sqlite/mysql

# ================================== #

# MySQL的连接要素

MySQL_host = ""
MySQL_port = 3306
MySQL_username = ''
MySQL_password = ''

# SQLite的连接要素

Database_path = r''  # sqlite数据库路径,不填默认.hoshino/uniform_score.db

# ================================== #

TESTING_MODE = True  # 开发/测试模式

# 此处集中配置peewee数据库模型与数据库名的对应关系，多个模型对应一个数据库请将key填写为tuple形式
# default代表没有找到对应数据库时使用的默认数据库

MySQL_database = {
	'default': 'default_db',
	('score_data', 'score_log'): 'score'
}


def get_database(name):
	if TESTING_MODE:
		return 'datatest'
	else:
		for k, v in MySQL_database.items():
			if name in k:
				return v
		return MySQL_database['default']

assert database_mode in ['mysql', 'sqlite'], 'Database mode is not supported: %s' % database_mode