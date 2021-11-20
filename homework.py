import exceptions as exc
import logging
import os
import requests
import telegram
import time
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO)

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения в телеграм."""
    try:
        bot.send_message(
            chat_id=TELEGRAM_CHAT_ID,
            text=message)
        message = 'Бот отправил сообщение'
        logging.info(message)
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(current_timestamp):
    """Запрос к api ENDPOINT."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT,
                                headers=HEADERS,
                                params=params)
    except Exception as error:
        message = f'Проблема с подключением: {error}'
        logging.error(message)
    else:
        if response.status_code != 200:
            message = (f'Сбой в работе программы: '
                       f'Эндпоинт {ENDPOINT} недоступен.'
                       f'Код ответа API: {response.status_code}')
            logging.error(message)
            raise exc.NoResponseError
    return response.json()


def check_response(response):
    """Валидация ответа ENDPOINT."""
    if 'homeworks' not in response:
        message = (
            'В ответе сервера отсутсвует домашнее заданее. Проверьте запрос.')
        logging.error(message)
        raise exc.NoHomeworksError

    if not isinstance(response, dict):
        message = (
            'Формат ответа - не словарь. Проверьте запрос.')
        logging.error(message)

    if not isinstance(response['homeworks'], list):
        message = (
            'Формат домашних работ - не список. Проверьте запрос.')
        logging.error(message)
        raise exc.HomeworksNotInListError

    return response.get('homeworks')


def parse_status(homework):
    """Определение статуса проверки проекта."""
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if (homework_status not in HOMEWORK_STATUSES
        ) or (homework_name is None
              ) or (homework_status is None):
        message = 'Статус домашней работы не определен.'
        logging.error(message)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия необходимых токенов."""
    if not all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)):
        return False
    return True


def main():
    """Основная логика работы бота."""
    if check_tokens():

        bot = telegram.Bot(token=TELEGRAM_TOKEN)
        current_timestamp = int(time.time())
        current_homework_status = ''
        while True:
            try:
                response = get_api_answer(current_timestamp)
                current_timestamp = response.get('current_date')
                homeworks = check_response(response)
            except Exception as error:
                message = f'Сбой в работе программы: {error}'
                logging.error(message)
                send_message(bot, message)
                time.sleep(RETRY_TIME)
            else:
                if homeworks:
                    homework = homeworks[0]
                    if current_homework_status != homework.get('status'):
                        current_homework_status = homework.get('status')
                        message = parse_status(homework)
                        send_message(bot, message)
                    else:
                        message = 'Статус проверки не изменен'
                        logging.debug(message)
                else:
                    message = 'Список проектов пуст. Не забыл запушить проект?'
                    logging.info(message)
                time.sleep(RETRY_TIME)

    else:
        missing_data = ((PRACTICUM_TOKEN, 'PRACTICUM_TOKEN'),
                        (TELEGRAM_TOKEN, 'TELEGRAM_TOKEN'),
                        (TELEGRAM_CHAT_ID, 'TELEGRAM_CHAT_ID'))
        message = ', '.join(
            [data[1] for data in missing_data if not data[0]])

        logging.debug(PRACTICUM_TOKEN)
        logging.debug(TELEGRAM_TOKEN)
        logging.debug(TELEGRAM_CHAT_ID)

        logging.critical(
            f'Отсутствует обязательная переменная окружения: {message}. '
            'Программа принудительно остановлена.')

        raise exc.MissingTokenError


# Вызов только если из файла
if __name__ == '__main__':
    main()
