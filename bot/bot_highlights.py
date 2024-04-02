import asyncio
from aiogram import Bot, Dispatcher, types
import datetime
import pytz


class MyBot:
    def __init__(self, token, db_manager, logger):
        self.bot = Bot(token=token)
        self.dp = Dispatcher(self.bot)
        self.db_manager = db_manager
        self.loop = asyncio.get_event_loop()
        self.selected_date = ""
        self.selected_hours = []
        self.selected_date_for_del = ""
        self.selected_hours_for_del = []
        self.logger = logger

    async def handle_contact(self, message: types.Message):
        if message.contact:
            full_name = str(message.from_user.first_name) + ' ' + str(message.from_user.last_name)
            await self.db_manager.save_user_to_db(message.from_user.id, full_name, message.contact.phone_number,
                                                  message.from_user.username)
            keyboard1 = types.InlineKeyboardMarkup()
            keyboard1.add(types.InlineKeyboardButton(text="Sing up", callback_data="start"))
            await self.bot.send_message(message.chat.id, 'Спасибо', reply_markup=types.ReplyKeyboardRemove())
            await self.bot.send_message(message.chat.id, 'Вы зарегистрированы!', reply_markup=keyboard1)
            self.logger.info(f"I have telephone - {message.contact.phone_number}")

        else:
            self.logger.info('telephone_not_me')

    async def handle_start(self, message: types.Message):
        user_id = message.from_user.id
        user_exists = await self.db_manager.check_user_in_db(user_id)
        keyboard = types.InlineKeyboardMarkup()
        if user_exists:
            keyboard.add(types.InlineKeyboardButton(text="Sing up", callback_data='start'))
        else:
            url_button1 = types.InlineKeyboardButton(text="Registration", callback_data='b')
            keyboard.add(url_button1)

        await message.answer('Привет, ' + message.from_user.first_name, reply_markup=keyboard)
        self.logger.info(f"/start - {message.from_user.username}")

    async def handle_my_timing(self, message: types.Message):
        user_id = message.from_user.id
        user_timing = await self.db_manager.get_user_timing_from_db(user_id)

        if user_timing:
            # Группируем записи по датам и сортируем время
            grouped_timings = {}
            for timing in user_timing:
                date_str = timing[0].strftime('%d.%m.%Y')
                time_str = timing[1]
                if isinstance(time_str, int):  # Check if time is an integer
                    time_str = f"{time_str:02d}:00"  # Assuming the time is represented as an hour
                else:
                    time_str = time_str.strftime('%H:%M')
                if date_str not in grouped_timings:
                    grouped_timings[date_str] = [time_str]
                else:
                    grouped_timings[date_str].append(time_str)

            # Сортируем время
            for times in grouped_timings.values():
                times.sort()

            # Формируем ответ
            response = "Ваша сохраненная информация:\n"
            for i, (date, times) in enumerate(grouped_timings.items(), start=1):
                response += f"{i}) Дата: {date}\n"
                for time in times:
                    response += f" - {time}\n"
        else:
            response = "У вас нет записей..."

        await message.reply(response)

    async def generate_user_dates_keyboard(self, user_id):
        keyboard = types.InlineKeyboardMarkup()
        # Получаем даты из БД для данного пользователя
        user_dates = await self.db_manager.get_user_dates_from_db(user_id)
        buttons_added = 0
        row = []
        for date in user_dates:
            callback_data = f"dated_{date}"
            row.append(types.InlineKeyboardButton(text=date.strftime('%d.%m %a'), callback_data=callback_data))
            buttons_added += 1
            if buttons_added % 4 == 0:  # Вставляем новый ряд после каждых 4 кнопок
                keyboard.row(*row)
                row = []  # Сбрасываем ряд для следующего набора кнопок

        if row:  # Добавляем оставшиеся кнопки в последний ряд
            keyboard.row(*row)

        # Добавляем кнопки для перехода к предыдущей и следующей неделе
        keyboard.row(types.InlineKeyboardButton(text="Удалить все", callback_data="del_all"))
        keyboard.row(types.InlineKeyboardButton(text="« Назад", callback_data="start"))

        return keyboard

    async def generate_time_keyboard_from_db(self, selected_hours=None, selected_date=None):
        keyboard = types.InlineKeyboardMarkup()
        row = []
        # Получаем доступные часы из БД для выбранной даты
        available_hours = await self.db_manager.get_available_hours_from_db(selected_date)

        for hour in available_hours:
            callback_data = f"untimed_{hour}"
            text = f"{'🔥 ' if selected_hours and hour in selected_hours else ''}{hour:02d}:00"
            row.append(types.InlineKeyboardButton(text=text, callback_data=callback_data))

            if len(row) == 3:  # Вставляем новый ряд после каждых 3 кнопок
                keyboard.row(*row)
                row = []

        if row:  # Добавляем оставшиеся кнопки в последний ряд
            keyboard.row(*row)

        # Если есть выбранные часы, добавляем кнопку "Удалить"
        if selected_hours:
            keyboard.row(types.InlineKeyboardButton(text="Удалить", callback_data="deltas_"))

        keyboard.row(types.InlineKeyboardButton(text="« Выбор даты", callback_data="del"))
        return keyboard

    @staticmethod
    async def generate_calendar_keyboard(start_date, sign):
        keyboard = types.InlineKeyboardMarkup()
        row = []
        for i in range(28):
            current_date = start_date + datetime.timedelta(days=i)
            callback_data = f"date_{current_date}"
            row.append(types.InlineKeyboardButton(text=current_date.strftime('%d.%m %a'), callback_data=callback_data))
            if len(row) == 4:  # Insert a new row after every fourth button
                keyboard.row(*row)
                row = []  # Reset the row for the next set of buttons
        if row:  # Add the remaining buttons in the last row
            keyboard.row(*row)
        if sign == 'next':
            keyboard.row(types.InlineKeyboardButton(text=" « ", callback_data="previous_week"))
        else:
            keyboard.row(types.InlineKeyboardButton(text=" » ", callback_data="next_week"))
        keyboard.row(types.InlineKeyboardButton(text="« Назад", callback_data="start"))
        return keyboard

    async def generate_next_week_keyboard(self, start_date):
        next_week_start = start_date + datetime.timedelta(days=28)
        return await self.generate_calendar_keyboard(next_week_start, 'next')

    async def generate_previous_week_keyboard(self, start_date):
        previous_week_start = start_date - datetime.timedelta()
        return await self.generate_calendar_keyboard(previous_week_start, 'previous')

    async def generate_time_keyboard(self, selected_hours=None, selected_date=None):
        keyboard = types.InlineKeyboardMarkup()
        row = []
        now_date = datetime.datetime.now().date()
        available_hours = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]  # Доступные часы
        if selected_date.date() == now_date:  # Определяем доступные часы исходя из текущего времени
            moscow_timezone = pytz.timezone('Europe/Moscow')
            current_hour = datetime.datetime.now(moscow_timezone).hour + 1  # Текущий час
            current_hour = max(min(current_hour, 22), 10)  # Ограничиваем текущий час от 10 до 22
            available_hours = [hour for hour in range(current_hour, 22)]
        busy_hours = set()
        if selected_date:
            busy_hours = await self.db_manager.get_busy_hours(selected_date)

        for hour in available_hours:
            if hour in busy_hours:
                continue

            callback_data = f"time_{hour:02d}"
            if selected_hours and hour in selected_hours:
                text = f"🏁 {hour:02d}:00"
            else:
                text = f"{hour:02d}:00"
            row.append(types.InlineKeyboardButton(text=text, callback_data=callback_data))

            if len(row) == 3:
                keyboard.row(*row)
                row = []

        if row:
            keyboard.row(*row)

        if selected_hours:
            keyboard.row(types.InlineKeyboardButton(text="Сохранить", callback_data="ok"))

        keyboard.row(types.InlineKeyboardButton(text="« Выбор даты", callback_data="aa"))

        return keyboard

    async def handle_callback(self, call: types.CallbackQuery):
        if call.message:
            if call.data == 'b':
                user_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
                phone = types.KeyboardButton(text='поделиться контактом', request_contact=True)
                user_markup.row(phone)
                await self.bot.send_message(call.from_user.id, 'Нажимай и продолжим', reply_markup=user_markup)
                await call.message.edit_reply_markup(reply_markup=None)
            elif call.data == 'start':
                keyboard = types.InlineKeyboardMarkup()
                self.selected_hours = []
                url_button1 = types.InlineKeyboardButton(text="Записаться", callback_data='a')
                url_button2 = types.InlineKeyboardButton(text="Удалить запись", callback_data='del')
                keyboard.add(url_button1)
                keyboard.add(url_button2)
                await call.message.edit_text("У тебя есть возможность..", reply_markup=keyboard)
            elif call.data == 'a':
                keyboard = await self.generate_calendar_keyboard(datetime.date.today(), 'current')
                await call.message.edit_text("Выберите дату:", reply_markup=keyboard)
            elif call.data == 'aa':
                keyboard = await self.generate_previous_week_keyboard(datetime.date.today())
                await call.message.edit_text("Выберите дату:", reply_markup=keyboard)
                self.selected_hours = []
            elif call.data == 'next_week':
                keyboard = await self.generate_next_week_keyboard(datetime.date.today())
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data == 'previous_week':
                keyboard = await self.generate_previous_week_keyboard(datetime.date.today())
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data.startswith('date_'):
                self.selected_date = call.data.split('_')[1]
                selected_date_obj = datetime.datetime.strptime(self.selected_date, '%Y-%m-%d')
                formatted_selected_date = selected_date_obj.strftime('%d.%m.%Y')
                keyboard = await self.generate_time_keyboard(selected_date=selected_date_obj)
                await call.message.edit_text(formatted_selected_date + ', выберите время:', reply_markup=keyboard)
            elif call.data.startswith('time_'):
                selected_time = int(call.data.split('_')[1])
                selected_date_obj = datetime.datetime.strptime(self.selected_date, '%Y-%m-%d')
                if selected_time in self.selected_hours:
                    self.selected_hours.remove(selected_time)
                else:
                    self.selected_hours.append(selected_time)
                keyboard = await self.generate_time_keyboard(self.selected_hours, selected_date=selected_date_obj)
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data == 'ok':
                # Сохраняем выбранную дату и время в БД
                selected_date_obj = datetime.datetime.strptime(self.selected_date, '%Y-%m-%d')
                await self.db_manager.insert_selected_schedule_in_db(call.from_user.id, selected_date_obj,
                                                                     self.selected_hours)
                formatted_selected_date = selected_date_obj.strftime('%d.%m.%Y')
                selected_hours_str = ', '.join([f"{hour:02d}:00" for hour in self.selected_hours])
                # Обновляем клавиатуру
                keyboard = types.InlineKeyboardMarkup()
                self.selected_hours = []
                self.selected_date = ""
                url_button1 = types.InlineKeyboardButton(text="Добавить запись", callback_data='a')
                url_button2 = types.InlineKeyboardButton(text="Удалить запись", callback_data='del')
                keyboard.add(url_button1)
                keyboard.add(url_button2)
                await call.message.edit_text(f"Вы записаны на - {formatted_selected_date} в {selected_hours_str}",
                                             reply_markup=keyboard)
            elif call.data == 'del':
                # Вывод клавиатуры с датами для удаления
                user_id_get = call.from_user.id
                keyboard = await self.generate_user_dates_keyboard(user_id_get)
                await call.message.edit_text("Выберите дату для удаления:", reply_markup=keyboard)
                self.selected_hours_for_del = []
            elif call.data.startswith('dated_'):
                # Выбираем дату для удаления
                self.selected_date_for_del = call.data.split('_')[1]
                selected_date_obj = datetime.datetime.strptime(self.selected_date_for_del, '%Y-%m-%d')
                formatted_selected_date = selected_date_obj.strftime('%d.%m.%Y')
                keyboard = await self.generate_time_keyboard_from_db(selected_date=self.selected_date_for_del)
                await call.message.edit_text(formatted_selected_date + ', выберите время:', reply_markup=keyboard)
            elif call.data.startswith('untimed_'):
                # Выбираем часы для удаления
                selected_time = int(call.data.split('_')[1])
                self.logger.info(
                    "find_selected_time_and_selected_hours: {}, {}".format(self.selected_hours_for_del, selected_time))
                if selected_time in self.selected_hours_for_del:
                    self.selected_hours_for_del.remove(selected_time)
                else:
                    self.selected_hours_for_del.append(selected_time)
                keyboard = await self.generate_time_keyboard_from_db(self.selected_hours_for_del,
                                                                     selected_date=self.selected_date_for_del)
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data == 'deltas_':
                # Удаляем выбранные записи из БД
                await self.db_manager.delete_selected_schedule_from_db(call.from_user.id, self.selected_date_for_del,
                                                                       self.selected_hours_for_del)
                keyboard = types.InlineKeyboardMarkup()
                self.selected_hours_for_del = []
                self.selected_date_for_del = ""
                url_button1 = types.InlineKeyboardButton(text="Добавить запись", callback_data='a')
                url_button2 = types.InlineKeyboardButton(text="Удалить запись", callback_data='del')
                keyboard.add(url_button1)
                keyboard.add(url_button2)
                await call.message.edit_text("Выбранные записи удалены", reply_markup=keyboard)
            elif call.data == 'del_all':
                # Удаляем все записи из БД
                await self.db_manager.delete_all_schedule_from_db(call.from_user.id)
                keyboard = types.InlineKeyboardMarkup()
                self.selected_hours_for_del = []
                self.selected_date_for_del = ""
                url_button1 = types.InlineKeyboardButton(text="Добавить запись", callback_data='a')
                url_button2 = types.InlineKeyboardButton(text="Удалить запись", callback_data='del')
                keyboard.add(url_button1)
                keyboard.add(url_button2)
                await call.message.edit_text("Все записи удалены", reply_markup=keyboard)
                pass
            else:
                self.logger.info(f"No interesting - {call.message}")

    async def start_bot(self):
        self.dp.register_message_handler(self.handle_contact, content_types=types.ContentType.CONTACT)
        self.dp.register_message_handler(self.handle_start, commands=['start'])
        self.dp.register_message_handler(self.handle_my_timing, commands=['timing'])

        self.dp.register_callback_query_handler(self.handle_callback)
        await self.bot.delete_webhook()
        await self.dp.start_polling()
