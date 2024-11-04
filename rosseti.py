import requests
from bs4 import BeautifulSoup
import warnings
from urllib3.exceptions import InsecureRequestWarning
import schedule
import time
import asyncio
from telegram import Bot
import os
from datetime import datetime, timedelta

# Подавляем предупреждения InsecureRequestWarning
warnings.simplefilter('ignore', InsecureRequestWarning)

# Прокси-сервер с российским IP
proxies = {
	'https': 'Вставьте ваш прокси, если необходимо.'
}

headers = {
	"Host": "rosseti-lenenergo.ru",
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
}

# Токен вашего бота и ID чата
BOT_TOKEN = 'Ваш токен телеграм бота.'
CHAT_ID = 'Ваш id чата куда будут присылать уведомления.'

# Создаем объект бота
bot = Bot(token=BOT_TOKEN)

# Храним прошлые результаты, чтобы пропускать старые упоминания
previous_results = set()

# Функция для отправки сообщения в Telegram
async def send_telegram_message(message):
	try:
		await bot.send_message(chat_id=CHAT_ID, text=message)
	except Exception as e:
		print(f"Ошибка при отправке сообщения в Telegram: {e}")

# Функция для парсинга страницы
def get_technical_works(url, proxies, headers):
	try:
		response = requests.get(url, headers=headers, proxies=proxies, verify=False)
		
		if response.status_code == 200:
			soup = BeautifulSoup(response.text, 'html.parser')
			works = soup.find_all('tr', class_='even')

			new_works = []

			for work in works:
				columns = work.find_all('td')

				if len(columns) > 6:
					# Извлекаем только даты и время (4-я, 5-я, 6-я, 7-я колонки)
					date_start = columns[3].text.strip()  # Начальная дата
					time_start = columns[4].text.strip()  # Начальное время
					date_end = columns[5].text.strip()    # Конечная дата
					time_end = columns[6].text.strip()    # Конечное время

					# Формируем строку с необходимой информацией
					work_info = f"Дата начала: {date_start} {time_start}, Дата окончания: {date_end} {time_end}"
					
					if 'Дятлицы' in columns[2].text:  # Проверяем, есть ли в 3-й колонке упоминание "Дятлицы"
						new_works.append(work_info)

			global previous_results
			new_mentions = [work for work in new_works if work not in previous_results]
			previous_results.update(new_mentions)

			return new_mentions if new_mentions else None
		else:
			print(f"Ошибка при получении страницы: {response.status_code}")
			return None
			
	except requests.exceptions.RequestException as e:
		print(f"Произошла ошибка при выполнении запроса: {e}")
		return None

# URL страницы
url = "https://185.26.120.53/planned_work/?reg=&city=&date_start=&date_finish=&res=&street=дятлицы"

# Функция, которая будет запускаться каждую минуту
async def check_for_updates():
	print("Скрипт работает...")  # Сообщение, чтобы видеть, что скрипт работает
	works = get_technical_works(url, proxies, headers)

	if works:
		for work in works:
			print("Найдена новая работа:", work)
			await send_telegram_message(f"Найдена новая работа: {work}")
	else:
		print("Ничего нового не найдено.")

# Функция для отправки ежедневного уведомления
async def send_daily_notification():
	message = "Скрипт работает нормально. Новых работ пока нет."
	await send_telegram_message(message)
	print("Ежедневное сообщение отправлено в Telegram.")

# Функция для управления задачами асинхронно
async def scheduler():
	while True:
		schedule.run_pending()
		await asyncio.sleep(1)

# Обертка для планировщика с использованием правильного цикла событий
def run_schedule():
	loop = asyncio.new_event_loop()  # Создаем новый цикл событий
	asyncio.set_event_loop(loop)  # Устанавливаем его как текущий
	loop.create_task(scheduler())  # Запускаем планировщик как задачу
	loop.run_forever()

# Планируем запуск функции check_for_updates каждую минуту
schedule.every(60).minutes.do(lambda: asyncio.create_task(check_for_updates()))
# Планируем ежедневное уведомление в 9:00
schedule.every().day.at("09:00").do(lambda: asyncio.create_task(send_daily_notification()))

# Бесконечный цикл для выполнения запланированных задач
run_schedule()
