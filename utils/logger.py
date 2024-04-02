import logging
import locale

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')


class Logger:
    def __init__(self, filename=None):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

        if filename:
            file_handler = logging.FileHandler(filename)
            file_handler.setLevel(logging.INFO)
            file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(file_formatter)
            self.logger.addHandler(file_handler)

    def get_logger(self):
        return self.logger

    def log_message(self, user_info, message_text):
        self.logger.info("\n -----")
        self.logger.info(
            f"Сообщение от {user_info['first_name']} {user_info['last_name']} {user_info['username']}. "
            f"(id = {user_info['id']}) \n Текст - {message_text}")
