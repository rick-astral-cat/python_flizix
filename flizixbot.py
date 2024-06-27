# Flizix bot class
import telepot
import configparser


class FlizixBot(telepot.helper.ChatHandler):
    def __init__(self, *args, **kwargs):
        super(FlizixBot, self).__init__(*args, **kwargs)
        config = configparser.ConfigParser()
        config.read('config.ini')

        # Extract DB info
        self.db_name = config.get('DATABASE', 'db_name')
        self.db_host = config.get('DATABASE', 'db_host')
        self.db_user = config.get('DATABASE', 'db_user')
        self.db_password = config.get('DATABASE', 'db_password')
        self.user = None

    def on_chat_message(self, msg):
        self.user = msg['from']['id']
        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text':
            print(msg)

    def on_close(self, ex):
        print(f"Conexión terminada con usuario {self.user} terminada")
