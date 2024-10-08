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
                    if query.strip().upper().startswith("INSERT"):
                        return db.lastrowid
        except Exception as e:
            raise e

    def on_chat_message(self, msg):
        # Save user ID on every interaction
        self.user = msg['from']['id']
        first_name = msg['from'].get('first_name', 'Unknown')
        last_name = msg['from'].get('last_name', '')
        self.username = first_name + (' ' + last_name if last_name else '')

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
                '/earn': lambda: self.add_month_earn(data),
                '/addRecPay': lambda: self.add_recurrent_payment(data)
            }
            result = msgItems.get(command, self.default)
            return result()
        else:
            self.sender.sendMessage('Command not recognized')

    def validRegex(self, regex, text):
        return re.match(regex, text) is not None

    def user_id_by_telegram_user(self):
        return self.execute_query("SELECT * FROM users WHERE telegram_id = %s", (self.user,), fetchone=True)

    def start(self):
        # TODO: Description of starting message
        # verify if user is already registered
        try:
            user = self.user_id_by_telegram_user()
            if user:
                self.sender.sendMessage(
                    "You already are registered on flizix, dont't worry and if you need help write /help")
            else:
                self.sender.sendMessage(
                    'Welcome to Flizix. This a private project, I will recolect your data if you decide stay. Write /addMe to register your user at database and start using this tool ;)')
        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")
            return

    def addMe(self, email):
        # this method add user to database and start using the tool
        try:
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
                db_user_id = self.execute_query(
                    "INSERT INTO USERS VALUES (NULL, %s, %s, %s)",
                    (self.username, email, self.user)
                )
                if db_user_id:
                    self.sender.sendMessage(
                        f"Congratulations, you are part of flizix member (by now). You user ID is: {db_user_id} "
                        f"in case you need it. You can start using commands to manage your finances")
        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")
            return

    def add_month_earn(self, data):
        # TODO: Create a registered user function to validate every command that needs user registration present
        # This will update/add month earn. By default, if not month is set it will take current month
        # If a record with this month is set it will just update the amount
        # Validate user is registered
        try:
            user_id = self.user_id_by_telegram_user()
            if not user_id:
                self.sender.sendMessage("Send /start to use this tool ;)")
                return
            # Split in case almost we receive month to set
            if data is None:
                self.sender.sendMessage("Use '/earn amount' or '/earn amount month' to add/update you month earns")
                return

            # Get month number and validate in case passed as parameter
            month = None
            year = datetime.datetime.now().year
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

            month_earn = self.execute_query(
                "SELECT * FROM month_data WHERE user = %s and date like %s",
                (user_id[0], f"{year}-{month}-%"),
                fetchone=True
            )
            if month_earn:
                self.execute_query(
                    "UPDATE month_data SET total_earn = %s WHERE user = %s AND id = %s",
                    (amount, user_id[0], month_earn[0])
                )
                self.sender.sendMessage(f"Month earn updated to: ${amount}")
            # Create new record
            else:
                inserted = self.execute_query(
                    "INSERT INTO month_data VALUES (NULL, %s, '%s-%s-01', %s, 0.00)",
                    (user_id[0], year, month, amount),
                )
                if inserted:
                    self.sender.sendMessage(f"Month earn registered with amount: ${amount}")

        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")
            return

    def add_recurrent_payment(self, data):
        # here we add a recurrent payment on database
        try:
            user_id = self.user_id_by_telegram_user()
            if not user_id:
                self.sender.sendMessage("Send /start to use this tool ;)")
                return

            if data is None or " " not in data:
                self.sender.sendMessage(
                    "Use '/addRecPay name amount' or 'addRecPay name amount comment' to add a recurrent payment you do"
                )
                return

            # Split data in name, amount and optional comment if exists
            name, amount, comment, *_ = data.split(" ") + [None,]*3
            # Validate valid number
            if not self.validRegex(r'^\d+$', amount):
                self.sender.sendMessage("The amount you sent is not a valid number")
                return
            else:
                amount = float(amount)

            # Database insert
            inserted = self.execute_query(
                "INSERT INTO recurrent_payments VALUES (NULL, %s, %s, %s, %s)",
                (user_id[0], name, amount, comment if comment else 'NULL')
            )
            if inserted:
                self.sender.sendMessage(f"Recurrent payment ({name}) registered")

        except Exception as e:
            self.sender.sendMessage(f"There was an error: {e}")
            return

    def default(self):
        # TODO: Write default message when wrong command
        self.sender.sendMessage('Command not recognized by default')

    def on_close(self, ex):
        print(f"Connection with user {self.user} closed or lost")
