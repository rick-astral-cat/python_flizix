import configparser
import flizixbot
import telepot
import time
from telepot.loop import MessageLoop
from telepot.delegate import pave_event_space, per_chat_id, create_open

if __name__ == '__main__':
    # Read Telegram Token from config.ini
    config = configparser.ConfigParser()
    config.read('config.ini')
    token = config['TELEGRAM']['token']

    bot = telepot.DelegatorBot(
        token,
        [
            pave_event_space()(
                per_chat_id(),
                create_open,
                flizixbot.FlizixBot,
                timeout=100
            )
        ]
    )

    MessageLoop(bot).run_as_thread()
    print("Telegram started...")
    while True:
        time.sleep(10)
