# Flizix bot class
import datetime
import textwrap

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

        # Global Commands
        self.global_commands = {
            'start': lambda: self.start(),
            'help': lambda data: self.help(data)
        }

        self.default_help = """
                Don't worry, you can use next <b>commands</b>:\n\n
                /start -> Init welcome message to flizix :)\n
                /help -> Show help according to current menu and all available commands in there. Also you can use \"/help command\"
                to extract help to specified command. Example: <u>/help earn</u>\n
                /addMe -> This command subscribe you to flizix platform\n
                /earn -> Set/Update month earn\n
                /recPay -> Enters to recurrent payments menu where you can manage them\n
            """.replace("  ", "")

        # All commands tree
        self.all_commands = {
            '/start': {
                'name': 'start',
                'command': self.global_commands['start'],
                'default': True,
                'avl_commands': '',
                'help': 'This is the welcome command, please. Use /help'
            },
            '/help': {
                'name': 'help',
                'command': self.global_commands['help'],
                'default': True,
                'avl_commands': '',
                'help': 'Really?'
            },
            '/addMe': {
                'name': 'addMe',
                'command': lambda data: self.addMe(data),
                'default': True,
                'avl_commands': '',
                'help': """Use to subscribe to flizix platform, it's free by now ;).\n
                    Use -> <i>/addMe email</i>
                    Example -> /addMe test@domain.com\n
                    Notes -> Your telegram name will be used as username on our database
                """.replace("  ", "")
            },
            '/earn': {
                'name': 'earn',
                'command': lambda data: self.add_month_earn(data),
                'default': False,
                'avl_commands': '',
                'help': """Use to set/update current or specific month earn.\n
                    Use -> <i>/earn amount</i>
                    Example -> /earn 15000
                    --------------------------
                    Use -> <i>/earn amount month</i>
                    Example -> /earn 15000 08
                """.replace("  ", "")
            },
            '/recPay': {
                'name': 'recPay',
                'command': lambda data: self.recurrent_payment(data),
                'default': True,
                'avl_commands': '',
                'help': """This menu let you manage your recurrent payments with next available commands\n
                    /addRecPay -> Add a new recurrent payment
                    """.replace("  ", "")
            },
            '/addRecPay': {
                'name': 'addRecPay',
                'command': lambda data: self.add_recurrent_payment(data),
                'default': False,
                'avl_commands': '',
                'help': """Use to add new recurrent payment like month payments.\n
                    Use -> <i>/addRecPay name amount</i>\n
                    Example: /addRecPay Gym 300
                    """.replace("  ", "")
            }
        }

        # Recurrent payments group commands
        self.c_rec_payments_group = {
            '/addRecPay': self.all_commands['/addRecPay']
        }

        # Default commands, used when every interaction starts
        self.default_commands = {
            '/start': self.all_commands['/start'],
            '/help': self.all_commands['/help'],
            '/addMe': self.all_commands['/addMe'],
            '/earn': self.all_commands['/earn'],
            '/recPay': self.all_commands['/recPay']
        }

        # Default available commands
        self.avl_commands = self.default_commands

        # Current command
        self.current_command = None

        # Last command
        self.last_command = None

        # Set initial default available commands
        for command in self.avl_commands:
            # We initiate recurrent payments command list with default and its own commands
            if command == "/recPay":
                self.avl_commands[command]['avl_commands'] = self.default_commands | self.c_rec_payments_group
                for sub_command in self.c_rec_payments_group:
                    self.c_rec_payments_group[sub_command]['avl_commands'] = self.avl_commands[command]['avl_commands']
            else:
                self.avl_commands[command]['avl_commands'] = self.default_commands

    def update_available_commands(self):
        # This method will update available commands on every interaction according to current command
        if self.current_command['name'] == "default" and self.last_command:
            self.avl_commands = self.last_command['avl_commands']
            return

        self.avl_commands = self.current_command['avl_commands']

    def set_last_command(self):
        # Set last command only when current command is different from default or help
        if self.current_command['name'] not in ['default', 'help']:
            self.last_command = self.current_command

    def get_default_commands(self):
        return self.default_commands

    def get_default_answer(self):
        return {
            'name': 'default',
            'command': lambda data: self.default(),
            'default': True,
            'avl_commands': self.default_commands,
            'help': self.default_help
        }

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
        msg_splitted = msg.split(' ', 1)
        if len(msg_splitted) > 1:
            command, data = msg_splitted
        else:
            command = msg_splitted[0]

        if self.validRegex(regex, command):
            self.current_command = self.avl_commands.get(command, self.get_default_answer())
            self.update_available_commands()
            self.current_command['command'](data)
            self.set_last_command()
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

    def recurrent_payment(self, data=None):
        self.sender.sendMessage(f"Recurrent payment menu entered")

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

    def help(self, command=None):
        #Search command's help if needed
        if command:
            for c in self.all_commands:
                cr = c.replace("/", "")
                if command == cr:
                    self.sender.sendMessage(self.all_commands[c]['help'], parse_mode="HTML")
                    return

            self.sender.sendMessage("Command not found :(", parse_mode="HTML")
            return
        # This avoids answer "Really?" which is default answer to help command as a joke!
        if self.current_command['name'] == 'help':
            if self.last_command is not None and self.last_command['name'] != "help":
                # If not command provided send current command help
                self.sender.sendMessage(self.last_command['help'], parse_mode="HTML")
            else:
                self.sender.sendMessage(self.default_help, parse_mode = "HTML")

    def default(self):
        # TODO: Write default message when wrong command
        self.sender.sendMessage('Command not recognized by default')

    def on_close(self, ex):
        print(f"Connection with user {self.user} closed or lost")
