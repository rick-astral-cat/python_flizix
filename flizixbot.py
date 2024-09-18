# Flizix bot class
import datetime

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

        # Telegram data
        self.user = None
        self.username = None

    def connect_db(self):
        """Return a database connection"""
        return mysql.connect(
            user=self.db_user,
            password=self.db_password,
            database=self.db_name
        )

    def execute_query(self, query, params=None, fetchone=False):
        """Execute a query and optionally fetch one record"""
        try:
            with self.connect_db() as cnx:
                with cnx.cursor() as db:
                    db.execute(query, params or ())
                    if fetchone:
                        return db.fetchone()
                    cnx.commit()
        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")

    def on_chat_message(self, msg):
        # Save user ID on every interaction
        self.user = msg['from']['id']
        self.username = msg['from']['first_name'] + ' ' + msg['from']['last_name']

        content_type, chat_type, chat_id = telepot.glance(msg)
        if content_type == 'text':
            self.handleText(msg)

    def handleText(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        msgTxt = msg['text']
        self.textMsgSwitch(msgTxt)

    def textMsgSwitch(self, msg):
        # Regex to validate commands of type "/command": /start, /addMe, /other123
        regex = r'^\/[a-z][a-z0-9A-Z]*$'

        # Split message in two. This means separate command and data
        data = None
        msg_spplitted = msg.split(' ', 1)
        if len(msg_spplitted) > 1:
            command, data = msg_spplitted
        else:
            command = msg_spplitted[0]

        if self.validRegex(regex, command):
            msgItems = {
                '/start': lambda: self.start(),
                '/addMe': lambda: self.addMe(data),
                '/earn': lambda: self.add_month_earn(data)
            }
            result = msgItems.get(command, self.default)
            return result()
        else:
            self.sender.sendMessage('Command not recognized')

    def validRegex(self, regex, text):
        return re.match(regex, text) is not None

    def user_id_by_telegram_user(self):
        try:
            cnx = mysql.connect(
                user=self.db_user,
                password=self.db_password,
                database=self.db_name)
            db = cnx.cursor()
            db.execute(f"select * from users where telegram_id = {self.user}")
            user = db.fetchone()
            cnx.close()
            return user
        except Exception as e:
            raise e

    def start(self):
        # TODO: Description of starting message
        # verify if user is already registered
        user = self.user_id_by_telegram_user()
        if user:
            self.sender.sendMessage(
                "You already are registered on flizix, dont't worry and if you need help write /help")
        else:
            self.sender.sendMessage(
                'Welcome to Flizix. This a private project, I will recolect your data if you decide stay. Write /addMe to register your user at database and start using this tool ;)')

    def addMe(self, email):
        # this method add user to database and start using the tool
        user = self.user_id_by_telegram_user()
        if user:
            self.sender.sendMessage('You are already registered and can use this amazing tool ;)')
        else:
            if email is None:
                self.sender.sendMessage('You email is missing. Please use command: /addMe test@example.com')
                return

            # Validate second parameter is a valid email
            if not self.validRegex(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email):
                self.sender.sendMessage('Write a valid email like: test@example.com')
                return

            try:
                cnx = mysql.connect(
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name)
                db = cnx.cursor()
                db.execute(f"insert into users values (NULL, '{self.username}', '{email}', {self.user})")
                cnx.commit()
                if db.lastrowid:
                    self.sender.sendMessage(
                        f"Congratulations, you are part of flizix member (by now). You user ID is: {db.lastrowid} in case you need it. You can start using commands to manage your finances")
                    cnx.close()
            except Exception as e:
                self.sender.sendMessage(
                    f'Something went wrong, try again later please :). This is the message in case you need it: {e}')

    def add_month_earn(self, data):
        # This will update/add month earn. By default, if not month is set it will take current month
        # If a record with this month is set it will just update the amount
        # Validate user is registered
        try:
            user_id = self.user_id_by_telegram_user()
            if not user_id:
                self.sender.sendMessage("Send /start to use this tool ;)")
                return
        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")
            return

        # Validate user is registered
        user_id = self.user_id_by_telegram_user()
        if not user_id:
            self.sender.sendMessage("Send /start to use this tool ;)")
            return

        # Split in case almost we receive month to set
        if data is None:
            self.sender.sendMessage("Use '/earn amount' or '/earn amount month' to add/update you month earns")
            return
        month = None
        if " " in data:
            amount, month = data.split(" ", 1)
            # Validate valid number
            if not self.validRegex(r'^\d+$', amount):
                self.sender.sendMessage("The amount you sent is not a valid number")
                return
            else:
                amount = int(amount)
            # Validate month
            if not self.validRegex(r"^(0[1-9]|1[0-2])$", month):
                self.sender.sendMessage("The month you introduce is no a valid month number. Use 01, 02 ... 12")
                return
        else:
            # Validate valid number
            if not self.validRegex(r'^\d+(\.\d{1,2})?$', data):
                self.sender.sendMessage("The amount you sent is not a valid number")
                return
            else:
                amount = float(data)
            month = f"{datetime.datetime.now().month:02d}"

        # Get record if exist on database for current telegram user
        user_id = self.user_id_by_telegram_user()
        year = datetime.datetime.now().year
        month_earn = None
        try:
            cnx = mysql.connect(
                user=self.db_user,
                password=self.db_password,
                database=self.db_name)
            db = cnx.cursor()
            db.execute(f"select * from month_data where user = {user_id[0]} and date like '{year}-{month}-%'")
            month_earn = db.fetchone()
            cnx.close()

        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")

        # Decide if update or create register for month earn
        # Update register
        if month_earn:
            try:
                cnx = mysql.connect(
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name)
                db = cnx.cursor()
                db.execute(
                    f"update month_data set total_earn = {amount} where user = {user_id[0]} and id = {month_earn[0]}"
                )
                cnx.commit()
                cnx.close()
                self.sender.sendMessage(f"Month earn updated to: ${amount}")

            except Exception as e:
                self.sender.sendMessage(f"There was an error: {e}")
        # Create new record
        else:
            try:
                cnx = mysql.connect(
                    user=self.db_user,
                    password=self.db_password,
                    database=self.db_name)
                db = cnx.cursor()
                db.execute(
                    f"insert into month_data values (NULL, {user_id[0]}, '{year}-{month}-01', {amount}, 0.00)"
                )
                cnx.commit()
                cnx.close()
                self.sender.sendMessage(f"Month earn registered with amount: ${amount}")

            except Exception as e:
                self.sender.sendMessage(f"There was an error: {e}")

        print(f"{amount} {month}")

    def default(self):
        # TODO: Write default message when wrong command
        self.sender.sendMessage('Command not recognized by default')

    def on_close(self, ex):
        print(f"Connection with user {self.user} lost")
