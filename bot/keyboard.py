from aiogram import types
import datetime
import pytz


class KeyboardGenerator:

    async def generate_user_dates_keyboard(self, user_dates):
        keyboard = types.InlineKeyboardMarkup()
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

    async def generate_time_keyboard_from_db(self, available_hours: set, selected_hours=None):
        keyboard = types.InlineKeyboardMarkup()
        row = []
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

    async def generate_time_keyboard(self, selected_date: datetime, busy_hours: set, selected_hours=None):
        keyboard = types.InlineKeyboardMarkup()
        row = []
        now_date = datetime.datetime.now().date()
        available_hours = [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21]  # Доступные часы
        if selected_date.date() == now_date:  # Определяем доступные часы исходя из текущего времени
            moscow_timezone = pytz.timezone('Europe/Moscow')
            current_hour = datetime.datetime.now(moscow_timezone).hour + 1  # Текущий час
            current_hour = max(min(current_hour, 22), 10)  # Ограничиваем текущий час от 10 до 22
            available_hours = [hour for hour in range(current_hour, 22)]

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
