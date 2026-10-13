import asyncio
import json
import os

import flet as ft
import flet_audio as fta

DATA_FILE = "workouts.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main(page: ft.Page):
    page.title = 'Мой фитнес-трекер'
    page.scroll = "auto"

    workouts = load_data()

    # --- Поля для упражнений ---
    exercise = ft.TextField(label='Упражнение', hint_text='Введи упражнение')
    weight = ft.TextField(label='Вес (кг)', keyboard_type=ft.KeyboardType.NUMBER)
    reps = ft.TextField(label='Повторения', keyboard_type=ft.KeyboardType.NUMBER)
    history = ft.Column()  # история тренировок

    # --- Общий счетчик тренировки ---
    workout_seconds = 0  # секунд по умолчанию
    workout_running = False  # флаг состояния тренировки
    workout_timer_text = ft.Text('00:00', size=36, weight='bold', color=ft.Colors.GREEN)  # отображение таймера тренировки

    # --- Таймер отдыха ---
    rest_seconds = 60  # секунд по умолчанию
    timer_display = ft.Text("01:00", size=36, weight='bold')  # отображение таймера
    rest_task = None  # переменная для хранения задачи таймера отдыха
    # sound_fta = fta.Audio(src='beep.mp3')
    # page.services.append(sound_fta)  # добавляем аудио сервис на страницу
    timer_picker = ft.CupertinoTimerPicker(
        value=rest_seconds,  # начальное значение таймера
        mode=ft.CupertinoTimerPickerMode.MINUTE_SECONDS,  # режим отображения минут и секунд
        on_change=lambda e: update_picker_value(e),  # обработчик изменения значения таймера

    )  

    def update_picker_value(e):  # функция обновления значения таймера при изменении пользователем
        nonlocal rest_seconds  # используем nonlocal для изменения переменной из внешней области видимости
        rest_seconds = e.data  # обновляем значение таймера
        timer_display.value = format_time(rest_seconds)  # обновляем отображение таймера

    def format_time(seconds):
        mins, secs = divmod(int(seconds), 60)  # форматируем время в минуты и секунды
        return f"{mins:02d}:{secs:02d}"

    # --- Общий счетчик тренировки (асинхронный) ---
    async def workout_timer():
        nonlocal workout_seconds, workout_running
        while workout_running:
            workout_timer_text.value = format_time(workout_seconds) # обновляем отображение таймера тренировки
            page.update()
            await asyncio.sleep(1)  # ждем 1 секунду
            workout_seconds += 1  # увеличиваем счетчик тренировки на 1 секунду

    # --- Функция обратного отсчета (асинхронная) ---
    async def countdown():
        nonlocal rest_seconds  # используем nonlocal для изменения переменной из внешней области видимости
        remaining = rest_seconds  # оставшееся время в секундах
        while remaining > 0:
            timer_display.value = format_time(remaining)  # обновляем отображение таймера
            page.update()  # обновляем страницу
            await asyncio.sleep(1)  # ждем 1 секунду
            remaining -= 1
        timer_display.value = '00:00'  # обновляем отображение таймера после завершения обратного отсчета
        page.update()  # обновляем страницу
        # await sound_fta.play()  # воспроизводим звуковой сигнал
        show_rest_over_dialog()
        


    # --- Функция запуска таймера тренировки ---
    def start_workout(e):
        nonlocal workout_running, workout_seconds
        if not workout_running:  # проверяем, что тренировка не запущена
            workout_running = True
            workout_seconds = 0  # сбрасываем счетчик тренировки
            workout_timer_text.value = "00:00"  # обновляем отображение таймера тренировки
            page.run_task(workout_timer)  # запускаем функцию таймера тренировки в отдельной задаче
            # page.run_task(countdown)  # запускаем функцию таймера отдыха в отдельной задаче

    # --- Функция остановки таймера тренировки ---
    def finish_workout(e):
        nonlocal workout_running, workout_seconds
        workout_running = False  # останавливаем таймер тренировки
        final_time = workout_timer_text.value # сохраняем финальное время тренировки
        dialog = ft.AlertDialog(
            title=ft.Text('Поздравляю, вы не сдолхи (сегодня :3)!'),
            content=ft.Text(f"Время тренировки: {final_time}"),
            actions=[
                ft.TextButton('Шо так тяжело то блять', on_click=lambda e: close_dialog(dialog))  # кнопка для закрытия диалогового окна
            ],
        )
        page.show_dialog(dialog)  # отображаем диалоговое окно на странице
        workout_timer_text.value = "00:00"  # сбрасываем отображение таймера тренировки
        workout_seconds = 0  # сбрасываем счетчик тренировки


    def start_timer(e):
        nonlocal rest_task
        if rest_task is not None:
            rest_task.cancel()  # отменяем предыдущую задачу таймера, если она существует
        rest_task = page.run_task(countdown)  # запускаем функцию обратного отсчета в отдельной задаче, чтобы не блокировать интерфейс пользователя

    def show_rest_over_dialog():  # функция для отображения диалогового окна после завершения таймера
        dialog = ft.AlertDialog(
            title=ft.Text('Отдых завершен!'),  # заголовок диалогового окна
            content=ft.Text('Пора ебашить, дрыщ!'),  # содержимое диалогового окна
            actions=[
                ft.TextButton('Поняв :3', on_click=lambda e: close_dialog(dialog))  # кнопка для закрытия диалогового окна
            ]
        )
        page.show_dialog(dialog)  # отображаем диалоговое окно на странице

    def close_dialog(dialog):  # функция для закрытия диалогового окна
        dialog.open = False  # закрываем диалоговое окно
        page.update()  # обновляем страницу после закрытия диалогового окна


    # --- Функция обновления истории ---
    def refresh_history():
        history.controls.clear()  # очищаем текущую историю
        for index, w in enumerate(workouts):
            history.controls.append(
                ft.ListTile(
                    ft.Text(f"{w['exercise']}"),
                    ft.Text(f"{w['weight']} кг x {w['reps']} повторений"),
                    on_click=fill_from_history,
                    data = index,  # запоминаем индекс
                )
            )

    save_button = ft.Button('Сохранить')  # кнопка для сохранения подхода
    cancel_button = ft.Button('Очистить', visible=False, color=ft.Colors.GREY)  # кнопка для очистки полей ввода

    def fill_from_history(e):  # функция заполнения полей из истории
        index = e.control.data  # получаем индекс выбранного подхода
        w = workouts[index]  # получаем данные подхода по индексу
        exercise.value = w['exercise']  # заполняем поле упражнения
        weight.value = w['weight']  # заполняем поле веса
        reps.value = w['reps']  # заполняем поле повторений
        cancel_button.visible = True  # делаем кнопку "Очистить" видимой
        # Прокрутим страницу к полям ввода, чтобы пользователь видел их
        page.scroll = "always"  # включаем автоматическую прокрутку страницы
        page.update()  # обновляем страницу после заполнения полей

    def cancel_edit(e):  # функция очистки полей ввода
        exercise.value = ''  # очищаем поле упражнения
        weight.value = ''  # очищаем поле веса
        reps.value = ''  # очищаем поле повторений
        cancel_button.visible = False  # скрываем кнопку "Очистить"
        page.update()


    def add_workout(e):  # функция добавления нового подхода
        if not exercise.value:  # проверяем, что поле упражнения не пустое
            return
        record = {
            'exercise': exercise.value,
            'weight': weight.value,
            'reps': reps.value
        }
        workouts.append(record)  # добавляем новый подход в список
        save_data(workouts)  # сохраняем данные в файл
        exercise.value = ''  # очищаем поле упражнения
        weight.value = ''  # очищаем поле веса
        reps.value = ''  # очищаем поле повторений
        cancel_button.visible = False  # скрываем кнопку "Очистить"
        refresh_history()  # обновляем историю после добавления нового подхода


    save_button.on_click = add_workout  # назначаем функцию добавления подхода на кнопку "Сохранить"
    cancel_button.on_click = cancel_edit  # назначаем функцию очистки полей на кнопку "Очистить"
 
    # --- Интерфейс пользователя ---
    page.add(
        ft.Text('Время:', size=24, weight='bold'),
        workout_timer_text,
        ft.Row([
            ft.Button('Старт', on_click=start_workout),
            ft.Button('Ну ладно, хорош!', on_click=finish_workout, color=ft.Colors.RED),
        ]),
        ft.Divider(),
        ft.Text('Добавить подход', size=24, weight='bold'),
        exercise,
        weight,
        reps,
        ft.Row([save_button, cancel_button]),
        ft.Divider(),
        ft.Text('Таймер отдыха', size=24, weight='bold'),
        timer_display,
        timer_picker,
        ft.Button('Старт', on_click=start_timer),
        ft.Divider(),
        ft.Text('История', size=20, weight='bold'),
        history
    )

    refresh_history()


ft.run(main)