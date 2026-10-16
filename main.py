import asyncio
import json
import os
from datetime import datetime

import flet as ft
import flet_audio as fta

DATA_FILE = "data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "exercises_base": [],
        "training_days": [],
        "workouts": []
    }

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def main(page: ft.Page):
    page.title = 'Мой фитнес-трекер'


    data = load_data()
    exercise_base = data["exercise_base"]
    training_days = data["training_days"]
    workouts = data["workouts"]

    # --- Поля для упражнений ---
    exercise = ft.TextField(label='Упражнение', hint_text='Введи упражнение')
    weight = ft.TextField(label='Вес (кг)', keyboard_type=ft.KeyboardType.NUMBER)
    reps = ft.TextField(label='Повторения', keyboard_type=ft.KeyboardType.NUMBER)

    # --- Общий счетчик тренировки ---
    workout_seconds = 0  # секунд по умолчанию
    workout_running = False  # флаг состояния тренировки
    workout_timer_text = ft.Text('00:00', size=36, weight='bold', color=ft.Colors.GREEN)  # отображение таймера тренировки
    start_workout_button = ft.Button('Стартуем')
    finish_workout_button = ft.Button('ОстановОчка', color=ft.Colors.RED, visible=False)


    # --- Таймер отдыха ---
    rest_seconds = 5  # секунд по умолчанию


    day_exercises_list = {
        day['id']: ft.Column() for day in training_days
    }

    tabs = ft.Tabs(
        selected_index=0,
        length=len(training_days),
        height=500,
        on_change=lambda e: on_tab_change(e),
        content=ft.Column(
            expand=True,
            controls=[
                ft.TabBar(
                    tabs=[
                        ft.Tab(label=day["name"])
                        for day in training_days
                    ],
                ),
                ft.TabBarView(
                    expand=True,
                    controls=[
                        ft.Container(
                            content=ft.Column(
                                controls=[
                                    ft.Text("Нпражнения:", size=18, weight='bold'),
                                    day_exercises_list[day['id']],
                                    ft.TextButton(
                                        "Добавить упражнение", 
                                        on_click=lambda e, d_id=day['id']: 
                                        asyncio.create_task(page.push_route(f"/add-to/{d_id}"))),
                                ]),
                            padding=20,)
                        for day in training_days],),],),)
    
    current_day_id = training_days[0]['id']  # какой сейчас день открыт

    def on_tab_change(e):
        nonlocal current_day_id
        current_day_id = training_days[int(e.data)]['id']
        refresh_exercises()

    def format_time(seconds):
        mins, secs = divmod(int(seconds), 60)  # форматируем время в минуты и секунды
        return f"{mins:02d}:{secs:02d}"

    timer_display = ft.Text(format_time(rest_seconds), size=36, weight='bold')  # отображение таймера
    rest_task = None  # переменная для хранения задачи таймера отдыха
    sound_fta = fta.Audio(src='beep.mp3', release_mode=fta.ReleaseMode.STOP,)
    auto_rest_switch = ft.Switch(label='Автостарт отдыха', value=True,)
    timer_picker = ft.CupertinoTimerPicker(
        value=rest_seconds,  # начальное значение таймера
        mode=ft.CupertinoTimerPickerMode.MINUTE_SECONDS,  # режим отображения минут и секунд
        on_change=lambda e: update_picker_value(e),  # обработчик изменения значения таймера
    )  

    def update_picker_value(e):  # функция обновления значения таймера при изменении пользователем
        nonlocal rest_seconds  # используем nonlocal для изменения переменной из внешней области видимости
        rest_seconds = e.data  # обновляем значение таймера
        timer_display.value = format_time(rest_seconds)  # обновляем отображение таймера


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
        await sound_fta.play()  # воспроизводим звуковой сигнал
        

    # --- Функция запуска таймера тренировки ---
    def start_workout(e):
        nonlocal workout_running, workout_seconds
        if not workout_running:  # проверяем, что тренировка не запущена
            workout_running = True
            workout_seconds = 0  # сбрасываем счетчик тренировки
            workout_timer_text.value = "00:00"  # обновляем отображение таймера тренировки
            finish_workout_button.visible = True
            page.run_task(workout_timer)  # запускаем функцию таймера тренировки в отдельной задаче

    # --- Функция остановки таймера тренировки ---
    def finish_workout(e):
        nonlocal workout_running, workout_seconds
        workout_running = False  # останавливаем таймер тренировки
        final_time = workout_timer_text.value # сохраняем финальное время тренировки
        dialog = ft.AlertDialog(
            title=ft.Text('Выпей теперь пивка!'),
            content=ft.Text(f"Время тренировки: {final_time}"),
            actions=[
                ft.TextButton('Лады :3', on_click=lambda e: close_dialog(dialog))  # кнопка для закрытия диалогового окна
            ],
        )
        page.show_dialog(dialog)  # отображаем диалоговое окно на странице
        workout_timer_text.value = "00:00"  # сбрасываем отображение таймера тренировки
        workout_seconds = 0  # сбрасываем счетчик тренировки
        finish_workout_button.visible = False

    start_workout_button.on_click = start_workout
    finish_workout_button.on_click = finish_workout

    def start_rest_timer():
        nonlocal rest_task
        if rest_task is not None:
            rest_task.cancel()
        rest_task = page.run_task(countdown)


    def start_timer(e):
        nonlocal rest_task
        if rest_task is not None:
            rest_task.cancel()  # отменяем предыдущую задачу таймера, если она существует
        start_rest_timer()
        rest_task = page.run_task(countdown)  # запускаем функцию обратного отсчета в отдельной задаче, чтобы не блокировать интерфейс пользователя


    def close_dialog(dialog):  # функция для закрытия диалогового окна
        dialog.open = False  # закрываем диалоговое окно
        page.update()  # обновляем страницу после закрытия диалогового окна


    # --- Функция обновления истории ---
    def refresh_exercises():
        for day_id, column in day_exercises_list.items():
            column.controls.clear()  # очищаем текущую историю
            day = next((d for d in training_days if d['id'] == day_id), None)
            if day is None:
                continue
            for ex_name in day.get('exercises', []):
                column.controls.append(
                    ft.ListTile(
                        title=ft.Text(ex_name),
                        on_click=lambda e, d_id=day_id, ex=ex_name:
                        asyncio.create_task(page.push_route(f"/exercise/{d_id}/{ex}")),
                    )
                )
        page.update()

    # def remove_workout(e, index):
    #     if 0 <= index <= len(workouts):
    #         del workouts[index]
    #     save_data(data)
    #     refresh_history()
    #     page.update()

    save_button = ft.Button('Сохранить')  # кнопка для сохранения подхода
    cancel_button = ft.Button('Очистить', visible=False, color=ft.Colors.GREY)  # кнопка для очистки полей ввода

    # def fill_from_history(e):  # функция заполнения полей из истории
    #     index = e.control.data  # получаем индекс выбранного подхода
    #     w = workouts[index]  # получаем данные подхода по индексу
    #     exercise.value = w['exercise']  # заполняем поле упражнения
    #     weight.value = w['weight']  # заполняем поле веса
    #     reps.value = w['reps']  # заполняем поле повторений
    #     cancel_button.visible = True  # делаем кнопку "Очистить" видимой
    #     page.update()  # обновляем страницу после заполнения полей

    # def cancel_edit(e):  # функция очистки полей ввода
    #     exercise.value = ''  # очищаем поле упражнения
    #     weight.value = ''  # очищаем поле веса
    #     reps.value = ''  # очищаем поле повторений
    #     cancel_button.visible = False  # скрываем кнопку "Очистить"
    #     page.update()


    # def add_workout(e):  # функция добавления нового подхода
    #     if not exercise.value:  # проверяем, что поле упражнения не пустое
    #         return
    #     record = {
    #         'day_id': current_day_id,  # актуальный день
    #         'exercise': exercise.value,
    #         'weight': weight.value,
    #         'reps': reps.value
    #     }
    #     workouts.append(record)  # добавляем новый подход в список
    #     save_data(data)  # сохраняем данные в файл
    #     exercise.value = ''  # очищаем поле упражнения
    #     weight.value = ''  # очищаем поле веса
    #     reps.value = ''  # очищаем поле повторений
    #     cancel_button.visible = False  # скрываем кнопку "Очистить"
    #     refresh_history()  # обновляем историю после добавления нового подхода
    #     if auto_rest_switch.value:
    #         start_rest_timer()  # автоматический запуск таймера после подхода


    # save_button.on_click = add_workout  # назначаем функцию добавления подхода на кнопку "Сохранить"
    # cancel_button.on_click = cancel_edit  # назначаем функцию очистки полей на кнопку "Очистить"

    # --- Добавляем главный экран ---
    def build_main_view():
        return ft.View(
            route="/",
            padding=0,
            controls=[
                ft.AppBar(title=ft.Text("Тренировки")),
                ft.Column(
                    controls=[
                        ft.Text('Время:', size=24, weight='bold'),
                        workout_timer_text,
                        ft.Row([start_workout_button, finish_workout_button]),
                        ft.Divider(),
                        tabs,
                        # ft.Text('Добавить подход', size=24, weight='bold'),
                        # exercise,
                        # weight,
                        # reps,
                        # ft.Row([save_button, cancel_button]),
                        # ft.Divider(),
                        # ft.Text('Таймер отдыха', size=24, weight='bold'),
                        # auto_rest_switch,
                        # timer_display,
                        # timer_picker,
                        # ft.Button('Старт', on_click=start_timer),
                        ft.Divider(),
                            ],
                            spacing=10,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                    ]
                )
 

    def build_muscle_picker_view(day_id):
        # Собираем уникальные группы мышц из базы
        muscles = sorted(set(ex.get('muscle', '') for ex in exercise_base if ex.get('muscle')))

        def go_to_muscle(e, m):
            asyncio.create_task(page.push_route(f"/add-to/{day_id}/{m}"))

        controls = [
            ft.AppBar(
                title=ft.Text("Выберите группу мыщц"),
                leading=ft.IconButton(
                    ft.Icons.ARROW_BACK,
                    on_click=lambda e: asyncio.create_task(page.push_route("/")),),),]

        if not muscles:
            controls.append(ft.Text("База упражнений пуста", size=16))
        else:
            controls.append(
                ft.Column(
                    controls=[
                        ft.ListTile(
                            title=ft.Text(m),
                            trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT),
                            on_click=lambda e, m=m: go_to_muscle(e, m), 
                        )
                        for m in muscles
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True
                )
            )
        return ft.View(
            route=f"/add-to/{day_id}",
            padding=0,
            controls=controls,
        )

    def build_exercise_picker_view(day_id, muscle):
        exercises = [ex for ex in exercise_base if ex.get('muscle') == muscle]

        def add_chosen(ex_name):
            for day in training_days:
                if day['id'] == day_id:
                    if ex_name not in day['exercises']:
                        day['exercises'].append(ex_name)
                    break
            save_data(data)
            asyncio.create_task(page.push_route("/"))

        def back_to_muscles(e):
            asyncio.create_task(page.push_route(f"/add-to/{day_id}"))

        controls = [
            ft.AppBar(
                title=ft.Text(muscle),
                leading=ft.IconButton(
                    icon=ft.Icons.ARROW_BACK,
                    on_click=back_to_muscles,
                ),
            ),
        ]

        if not exercises:
            controls.append(ft.Text("В этой группе пока нет упражнений", size=16))
        else:
            controls.append(
                ft.Column(
                    controls=[
                        ft.ListTile(
                            title=ft.Text(ex['name']),
                            subtitle=ft.Text(ex.get('description', '')),
                            on_click=lambda e, n=ex['name']: add_chosen(n)
                        )
                        for ex in exercises
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                )
            )

        return ft.View(
            route=f"/add-to/{day_id}/{muscle}",
            padding=0,
            controls=controls,
            )

    async def view_pop(e):
        if e.view is not None:
            page.views.remove(e.view)
            top_view = page.views[-1]
            await page.push_route(top_view.route)
    page.on_view_pop = view_pop


    def build_exercise_view(day_id, ex_name):

        def save_approach(e):
            count = sum(1 for w in workouts if w.get('day_id') == day_id and w.get('exercise') == ex_name) + 1

            record = {
                'day_id': day_id,
                'exercise': ex_name,
                'weight': weight_field.value,
                'reps': reps_field.value,
                'comment': comment_field.value,
                'date': datetime.now().strftime('%Y-%m-%d'),
            }

            workouts.append(record)
            save_data(data)
            weight_field.value = ''
            reps_field.value = ''
            comment_field.value = ''
            rebuild_history()
            if auto_rest_switch.value:
                start_rest_timer()

        def rebuild_history():
            history_column.controls.clear()
            # собираем записи по этому упражнению
            entries = [
                w for w in workouts if w.get('day_id') == day_id and w.get('exercise') == ex_name
            ]
            # группируем по дате
            by_date = {}
            for w in entries:
                d = w.get('date', 'Без даты')
                by_date.setdefault(d, []).append(w)

            total = len(entries)
            count_text.value = f"Подходов выполнено: {total}"

            # Сортируем даты по убыванию
            for date in sorted(by_date.keys(), reverse=True):
                # Форматируем дату красиво
                if date != "Без даты":
                    try:
                        dt = datetime.strptime(date, '%Y-%m-%d')
                        pretty = dt.strftime('%d.%m.%y, %a')
                    except Exception:
                        pretty = date
                else:
                    pretty = date

                history_column.controls.append(ft.Text(pretty, size=16, weight='bold'))

                # записи этого дня в обратном порядке
                day_entries = list(reversed(by_date[date]))
                for i, w in enumerate(day_entries, start=1):
                    num = total - (i - 1)
                    comment = w.get('comment', '')
                    comment_str = f" - {comment}" if comment else ''
                    history_column.controls.append(
                        ft.Text(
                            f" #{num} {w.get('weight', '')} кг {w.get('reps', '')}{comment_str}"
                        )
                    )
            page.update()

        # --- Поля ввода ---
        weight_field = ft.TextField(label='Вес (кг)', keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        reps_field = ft.TextField(label='Повторения', keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        comment_field = ft.TextField(label='Коментарий', expand=2)
        count_text = ft.Text('Подходов выполено: 0', size=16, weight='bold')
        history_column = ft.Column()

        add_button = ft.Button('Добавить подход', on_click=save_approach)

        # --- AppBar ---
        appbar = ft.AppBar(
            title=ft.Text(ex_name),
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: asyncio.create_task(page.push_route("/")),
            ),
        )

        # --- Содержимое ---
        content = ft.Column(
            controls=[
                count_text,
                ft.Divider(),
                ft.Text('Время отдыха', size=18, weight='bold'),
                auto_rest_switch,
                timer_display,
                timer_picker,
                ft.Button('Старт', on_click=start_timer),
                ft.Divider(),
                ft.Text('Новый подход', size=18, weight='bold'),
                ft.Row([weight_field, reps_field]),
                comment_field,
                add_button,
                ft.Divider(),
                ft.Text('История', size=18, weight='bold'),
                history_column,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        # --- Первая отрисовка истории ---
        rebuild_history()

        return ft.View(
            route=f"/add-to/{day_id}/{ex_name}",
            padding=0,
            controls=[appbar, content]
        )


    # --- Роутер ---
    def on_route_change(e):
        page.views.clear()
        route = page.route
        if route.startswith("/add-to/"):
            parts = route.split("/")
            day_id = parts[2]
            if len(parts) >= 4 and parts[3]:
                page.views.append(build_exercise_picker_view(day_id, parts[3]))
            else:
                page.views.append(build_muscle_picker_view(day_id))
        elif route.startswith("/exercise/"):
            parts = route.split("/")
            day_id = parts[2]
            ex_name = parts[3]
            page.views.append(build_exercise_view(day_id, ex_name))
        else:
            page.views.append(build_main_view())
            refresh_exercises()
        page.update()
    page.on_route_change = on_route_change
    on_route_change(None)
    refresh_exercises()

ft.run(main)