import configparser

DB_NAME = None
DB_HOST = None
DB_USER = None
DB_PASSWORD = None


def read_config():
    global DB_NAME
    global DB_HOST
    global DB_USER
    global DB_PASSWORD

    config = configparser.ConfigParser()
    config.read('config.ini')

    # Extract DB info
    DB_NAME = config.get('DATABASE', 'db_name')
    DB_HOST = config.get('DATABASE', 'db_host')
    DB_USER = config.get('DATABASE', 'db_user')
    DB_PASSWORD = config.get('DATABASE', 'db_password')

if __name__ == '__main__':
    # Read config.ini data
    read_config()
    print(DB_NAME, DB_HOST, DB_USER, DB_PASSWORD)
