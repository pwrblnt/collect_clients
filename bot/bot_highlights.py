import asyncio
from aiogram import Bot, Dispatcher, types
import datetime
from bot.keyboard import KeyboardGenerator


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
        self.keyboard_generator = KeyboardGenerator()

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

    async def handle_callback(self, call: types.CallbackQuery):
        if call.message:
            if call.data == 'b':
                user_markup = types.ReplyKeyboardMarkup(one_time_keyboard=True)
                phone = types.KeyboardButton(text='поделиться контактом', request_contact=True)
                user_markup.row(phone)
                await self.bot.send_message(call.from_user.id, 'Нажимай и продолжим', reply_markup=user_markup)
                await call.message.edit_reply_markup(reply_markup=None)
                self.logger.info(f"Registration - {call.from_user.username}")
            elif call.data == 'start':
                keyboard = types.InlineKeyboardMarkup()
                self.selected_hours = []
                url_button1 = types.InlineKeyboardButton(text="Записаться", callback_data='a')
                url_button2 = types.InlineKeyboardButton(text="Удалить запись", callback_data='del')
                keyboard.add(url_button1)
                keyboard.add(url_button2)
                self.logger.info(f"Sing up - {call.from_user.username}")
                await call.message.edit_text("У тебя есть возможность..", reply_markup=keyboard)
            elif call.data == 'a':
                keyboard = await self.keyboard_generator.generate_calendar_keyboard(datetime.date.today(), 'current')
                await call.message.edit_text("Выберите дату:", reply_markup=keyboard)
            elif call.data == 'aa':
                keyboard = await self.keyboard_generator.generate_previous_week_keyboard(datetime.date.today())
                await call.message.edit_text("Выберите дату:", reply_markup=keyboard)
                self.selected_hours = []
            elif call.data == 'next_week':
                keyboard = await self.keyboard_generator.generate_next_week_keyboard(datetime.date.today())
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data == 'previous_week':
                keyboard = await self.keyboard_generator.generate_previous_week_keyboard(datetime.date.today())
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data.startswith('date_'):
                self.selected_date = call.data.split('_')[1]
                selected_date_obj = datetime.datetime.strptime(self.selected_date, '%Y-%m-%d')
                formatted_selected_date = selected_date_obj.strftime('%d.%m.%Y')
                busy_hours = await self.db_manager.get_busy_hours(selected_date_obj)
                keyboard = await self.keyboard_generator.generate_time_keyboard(selected_date=selected_date_obj,
                                                                                busy_hours=busy_hours)
                await call.message.edit_text(formatted_selected_date + ', выберите время:', reply_markup=keyboard)
            elif call.data.startswith('time_'):
                selected_time = int(call.data.split('_')[1])
                selected_date_obj = datetime.datetime.strptime(self.selected_date, '%Y-%m-%d')
                if selected_time in self.selected_hours:
                    self.selected_hours.remove(selected_time)
                else:
                    self.selected_hours.append(selected_time)
                busy_hours = await self.db_manager.get_busy_hours(selected_date_obj)
                keyboard = await self.keyboard_generator.generate_time_keyboard(selected_date=selected_date_obj,
                                                                                busy_hours=busy_hours,
                                                                                selected_hours=self.selected_hours)
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
            elif call.data == 'del':  # Вывод клавиатуры с датами для удаления
                user_id_get = call.from_user.id
                user_dates = await self.db_manager.get_user_dates_from_db(
                    user_id_get)  # Получаем даты из БД для данного пользователя
                keyboard = await self.keyboard_generator.generate_user_dates_keyboard(user_dates)
                await call.message.edit_text("Выберите дату для удаления:", reply_markup=keyboard)
                self.selected_hours_for_del = []
            elif call.data.startswith('dated_'):  # Выбираем дату для удаления
                self.selected_date_for_del = call.data.split('_')[1]
                selected_date_obj = datetime.datetime.strptime(self.selected_date_for_del, '%Y-%m-%d')
                formatted_selected_date = selected_date_obj.strftime('%d.%m.%Y')
                # Получаем доступные часы из БД для выбранной даты
                available_hours = await self.db_manager.get_available_hours_from_db(selected_date_obj)
                keyboard = await self.keyboard_generator.generate_time_keyboard_from_db(available_hours=available_hours)
                await call.message.edit_text(formatted_selected_date + ', выберите время:', reply_markup=keyboard)
            elif call.data.startswith('untimed_'):  # Выбираем часы для удаления
                selected_time = int(call.data.split('_')[1])
                self.logger.info(
                    "find_selected_time_and_selected_hours: {}, {}".format(self.selected_hours_for_del, selected_time))
                if selected_time in self.selected_hours_for_del:
                    self.selected_hours_for_del.remove(selected_time)
                else:
                    self.selected_hours_for_del.append(selected_time)
                selected_date_obj = datetime.datetime.strptime(self.selected_date_for_del, '%Y-%m-%d')
                available_hours = await self.db_manager.get_available_hours_from_db(selected_date_obj)
                keyboard = await self.keyboard_generator.generate_time_keyboard_from_db(
                    selected_hours=self.selected_hours_for_del, available_hours=available_hours)
                await call.message.edit_reply_markup(reply_markup=keyboard)
            elif call.data == 'deltas_':  # Удаляем выбранные записи из БД
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
            elif call.data == 'del_all':  # Удаляем все записи из БД
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
