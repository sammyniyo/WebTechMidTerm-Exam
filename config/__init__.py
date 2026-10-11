import pymysql

# Django 5.2 expects mysqlclient >= 2.2.1. PyMySQL is the pure-Python driver.
pymysql.version_info = (2, 2, 1, "final", 0)
pymysql.install_as_MySQLdb()
