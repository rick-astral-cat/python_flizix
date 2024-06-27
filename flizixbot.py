# Flizix bot class
import telepot
import configparser
import re
import mysql.connector as mysql


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
        # Save user ID on every interaction
        self.user = msg['from']['id']

        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text':
            self.handleText(msg)

    def handleText(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        msgTxt = msg['text']
        self.textMsgSwitch(msgTxt)

    def textMsgSwitch(self, msg):
        regex = r'^\/[a-z][a-z0-9]*$'
        if self.validRegex(regex, msg):
            msgItems = {
                '/start': self.start,
            }
            result = msgItems.get(msg, self.default)
            return result()
        else:
            self.sender.sendMessage('Command not recognized')

    def validRegex(self, regex, text):
        return re.match(regex, text) is not None

    def checkTelegramUserOnDB(self):
        try:
            cnx = mysql.connect(
                user=self.db_user,
                password=self.db_password,
                database=self.db_name)
            db = cnx.cursor()
            db.execute(f"select * from users where telegram_id = {self.user}")
            user = db.fetchall()
            cnx.close()
            return user
        except:
            self.sender.sendMessage('Something went wrong, try again later please :)')

    def start(self):
        # TODO: Description of starting message
        # verify if user is already registered
        user = self.checkTelegramUserOnDB()
        if user:
            self.sender.sendMessage(
                "You already are registered on flizix, dont't worry and if you need help write /help")
        else:
            self.sender.sendMessage(
                'Welcome to Flizix. This a private project, I will recolect your data if you decide stay. Write /addMe to register your user at database and start using this tool ;)')

    def addMe(self):
        # this method add user to database and start using the tool
        pass


    def default(self):
        # TODO: Write default message when wrong command
        self.sender.sendMessage('Command not recognized by default')

    def on_close(self, ex):
        print(f"Connection with user {self.user} lost")
