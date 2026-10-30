import asyncio
import json
import os
from datetime import datetime

import flet as ft
import flet_audio as fta

API_URL = "http://127.0.0.1:8000"
DATA_FILE = "data.json"

def load_data():
    default_data =  {"exercise_base": [],
            "training_days": [
            {"id": "day_1", "name": "Понедельник", "exercises": []},
            {"id": "day_2", "name": "Вторник", "exercises": []},
            {"id": "day_3", "name": "Среда", "exercises": []},
            {"id": "day_4", "name": "Четверг", "exercises": []},
            {"id": "day_5", "name": "Пятница", "exercises": []},
            {"id": "day_6", "name": "Суббота", "exercises": []},
            {"id": "day_7", "name": "Воскресенье", "exercises": []}
            ],
            "workouts": []}
    
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for key in default_data.items():
                    if key not in data:
                        data[key] = default_data[key]
                return data
        except (json.JSONDecodeError, ValueError):
            return default_data
    return default_data
    

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def show_login_screen(page: ft.Page):
    page.views.clear()

    username_field = ft.TextField(label="Логин", weight=300)
    password_field = ft.TextField(label="Пароль", password=True, weight=300)
    error_text = ft.Text("", color=ft.Colors.RED)

    def login(e):
        import httpx
        try:
            # Отправляем запрос на сервер
            response = httpx.post(
                f"{API_URL}/token",
                data={"username": username_field.value, "password": password_field.value}
            )

            if responce.status_code == 200:
                # Если успех - сохраняем токен
                token = response.json()["access_token"]
                page.client_storage.set("auth_token", token)

                # Перезапускаем main 
                page.ciews.clear()
                main(page)  # Запускаем main, он увидит токен и загрузит данные 
            else:
                error_text.value = "Неверный логин или пароль"
                page.update()
        except Exception as ex:
            error_text.value = f"Ошибка сети: {str(ex)}"
            page.update()


    login_button = ft.Button("Войти", on_click=login)

    view = ft.View(
        route="/login",
        controls = [
            ft.Column(
                controls = [
                    ft.Text("Вход в фитнес-трекер", size=24, weight="bold"),
                    username_field,
                    password_field,
                    error_text,
                    login_button,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=20,
            )
        ],
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
    )

    page.views.append(view)
    page.update()

def main(page: ft.Page):
    page.title = 'Мой фитнес-трекер'

    # Проверка авторизации
    token = page.client_storage.get("auth_token")

    if not token:
        # Если нет токена показываем экран логина
        show_login_screen(page)
        return

    data = load_data()
    exercise_base = data.get("exercise_base", [])
    training_days = data.get("training_days", [])
    workouts = data.get("workouts", [])


    # --- Общий счетчик тренировки ---
    workout_seconds = 0  # секунд по умолчанию
    workout_running = False  # флаг состояния тренировки
    workout_timer_text = ft.Text('00:00', size=36, weight='bold', color=ft.Colors.GREEN)  # отображение таймера тренировки
    start_workout_button = ft.Button('Стартуем')
    finish_workout_button = ft.Button('ОстановОчка', color=ft.Colors.RED, visible=False)
    stats_text = ft.Text("Сегодня: 0 подходов, 0 кг", size=20, color=ft.Colors.GREY)  # статистика подходов за тренировочный день
    stats_reset_time = {'value': None}


    def reset_stats(e):
        stats_reset_time['value'] = datetime.now()
        stats_text.value = "Сегодня: 0 подходов, 0 кг"
        page.update()


    reset_stats_button = ft.IconButton(
        icon=ft.Icons.REFRESH,
        icon_color=ft.Colors.GREY,
        icon_size=18,
        tooltip='Сбросить статистику',
        on_click=reset_stats
    )


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
                                    ft.Text("Упражнения:", size=18, weight='bold'),
                                    day_exercises_list[day['id']],
                                    ft.TextButton(
                                        "Добавить упражнение", 
                                        on_click=lambda e, d_id=day['id']: 
                                        asyncio.create_task(page.push_route(f"/add-to/{d_id}"))),
                                ]),
                            padding=20,)
                        for day in training_days],),],),)
    
    current_day_id = training_days[0]['id'] if training_days else None  # какой сейчас день открыт

    def on_tab_change(e):
        nonlocal current_day_id
        current_day_id = training_days[int(e.data)]['id']
        refresh_exercises()

    def format_time(seconds):
        mins, secs = divmod(int(seconds), 60)  # форматируем время в минуты и секунды
        return f"{mins:02d}:{secs:02d}"

    def update_stats_display():
        sets, tonnage = get_today_stats()
        stats_text.value = f"Сегодня: {sets} подходов, {int(tonnage)} кг"
        page.update()

    def get_today_stats():
        today = datetime.now().strftime("%Y-%m-%d")
        reset_at = stats_reset_time['value']

        today_workouts = []
        for w in workouts:
            if w.get('date') != today:
                continue
            if reset_at is not None:
                # если сброс был выполнен, берем только подходы, сделанные после него
                w_time_str = w.get('timestamp')
                if w_time_str:
                    w_time = datetime.fromisoformat(w_time_str)
                    if w_time < reset_at:
                        continue
            today_workouts.append(w)

        total_sets = len(today_workouts)
        total_tonnage = 0
        for w in today_workouts:
            try:
                weight = float(w.get('weight', 0) or 0)
                reps = int(w.get('reps', 0) or 0)
                total_tonnage += weight * reps
            except (ValueError, TypeError):
                pass
        return total_sets, total_tonnage


    sound_fta = fta.Audio(src='beep.mp3', release_mode=fta.ReleaseMode.STOP,)


    # --- Общий счетчик тренировки (асинхронный) ---
    async def workout_timer():
        nonlocal workout_seconds, workout_running
        while workout_running:
            workout_timer_text.value = format_time(workout_seconds) # обновляем отображение таймера тренировки
            page.update()
            await asyncio.sleep(1)  # ждем 1 секунду
            workout_seconds += 1  # увеличиваем счетчик тренировки на 1 секунду


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


    def close_dialog(dialog):  # функция для закрытия диалогового окна
        dialog.open = False  # закрываем диалоговое окно
        page.update()  # обновляем страницу после закрытия диалогового окна

    def remove_exercise_from_day(day_id, ex_index):
        for day in training_days:
            if day['id'] == day_id:
                if 0 <= ex_index < len(day['exercises']):
                    day['exercises'].pop(ex_index)
                break
        save_data(data)
        refresh_exercises()
        page.update()


    # --- Функция обновления истории ---
    def refresh_exercises():
        for day_id, column in day_exercises_list.items():
            column.controls.clear()  # очищаем текущую историю
            day = next((d for d in training_days if d['id'] == day_id), None)
            if day is None:
                continue
            for ex_index, ex_name in enumerate(day.get('exercises', [])):
                dismissible = ft.Dismissible(
                    content=ft.ListTile(
                        title=ft.Text(ex_name),
                        on_click=lambda e, d_id=day_id, ex=ex_name:
                        asyncio.create_task(page.push_route(f"/exercise/{d_id}/{ex}")),
                    ),
                    dismiss_direction=ft.DismissDirection.END_TO_START,
                    background=ft.Container(
                        bgcolor=ft.Colors.RED,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        padding=20
                    ),
                    secondary_background=ft.Container(
                        content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE),
                        bgcolor=ft.Colors.RED,
                        alignment=ft.Alignment.CENTER_RIGHT,
                        padding=20,
                    ),
                    on_dismiss=lambda e, d_id=day_id, idx=ex_index:
                    remove_exercise_from_day(d_id, idx),
                    key=f"{day_id}_{ex_index}_{ex_name}",
                )
                column.controls.append(dismissible)
        page.update()


    # --- Добавляем главный экран ---
    def build_main_view():
        return ft.View(
            route="/",
            padding=0,
            controls=[
                ft.AppBar(
                    title=ft.Text("Тренировки"),
                    actions=[
                        ft.IconButton(
                        icon=ft.Icons.LIBRARY_BOOKS,
                        tooltip='База упражнений',
                        on_click=lambda e:asyncio.create_task(page.push_route("/base")),
                        ),
                    ],
                ),
                ft.Column(
                    controls=[
                        ft.Text('Время:', size=24, weight='bold'),
                        workout_timer_text,
                        ft.Row([stats_text, reset_stats_button]),
                        ft.Row([start_workout_button, finish_workout_button]),
                        ft.Divider(),
                        tabs,
                        ft.Divider(),
                            ],
                            spacing=10,
                            scroll=ft.ScrollMode.AUTO,
                            expand=True,
                        ),
                    ],
                )
                    
                

    def build_base_view():
        # Функция для обновления списка на экране
        def refresh_base_list():
            base_list.controls.clear()
            # Группируем упражнения по мышцам
            by_muscle = {}
            for idx, ex in enumerate(exercise_base):
                muscle = ex.get('muscle', 'Без группы')
                by_muscle.setdefault(muscle, []).append((idx, ex))

            for muscle, items in sorted(by_muscle.items()):
                base_list.controls.append(
                    ft.Text(muscle, size=18, weight='bold', color=ft.Colors.PRIMARY)
                )
                for idx, ex in items:
                    base_list.controls.append(
                        ft.ListTile(
                            title=ft.Text(ex['name']),
                            subtitle=ft.Text(ex.get('description', '')),
                            trailing=ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        on_click=lambda e, i=idx: open_edit_exercise(i),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        icon_color=ft.Colors.RED,
                                        on_click=lambda e, i=idx: delete_exercise(i),
                                    ),
                                ],
                                tight=True
                            ),
                        )
                    )
                page.update()

        def delete_exercise(idx):
            if not (0 <= idx < len(exercise_base)):
                return

            ex_name = exercise_base[idx]['name']

            def confirm_delete(e):
                # Удаляем упражнение из базы
                del exercise_base[idx]
                # Заодно убираем его из всех тренировочных дней
                for day in training_days:
                    if ex_name in day.get('exercise', []):
                        day['exercise'].remove(ex_name)
                save_data(data)
                page.pop_dialog()
                refresh_base_list()

            dialog = ft.AlertDialog(
                title=ft.Text('Удалить упражнение'),
                content=ft.Text(f'"{ex_name}" будет удалено из базы и из всех тренировочных дней. Это действие нельзя отменить'),
                actions=[
                    ft.TextButton('Отмена', on_click=lambda e: page.pop_dialog()),
                    ft.TextButton('Удалить', on_click=confirm_delete, style=ft.ButtonStyle(color=ft.Colors.RED),
                    ),
                ],
            )
            page.show_dialog(dialog)


        def open_edit_exercise(idx):
            ex = exercise_base[idx]
            name_field = ft.TextField(label='Название', value=ex.get('name', ''))
            muscle_field = ft.TextField(label='Группа мышц', value=ex.get('muscle', ''))
            desc_field = ft.TextField(label='Описание', value=ex.get('description', ''), multiline=True)

            def save_edit(e):
                if not name_field.value:
                    return
                exercise_base[idx] = {
                    'name': name_field.value,
                    'muscle': muscle_field.value,
                    'description': desc_field.value
                }
                save_data(data)
                page.pop_dialog()
                refresh_base_list()

            dialog = ft.AlertDialog(
                title='Редактировать упражнение',
                content=ft.Column([name_field, muscle_field, desc_field], tight=True),
                actions=[ft.TextButton('Сохранить', on_click=save_edit),
                         ft.TextButton('Отмена', on_click=lambda e: page.pop_dialog()),
                         ],
            )
            page.show_dialog(dialog)

        def open_add_exercise(e):
            name_field = ft.TextField(label='Название')
            muscle_field = ft.TextField(label='Группа мышц')
            desc_field = ft.TextField(label='Описание', multiline=True)

            def save_new(e):
                if not name_field.value:
                    return
                exercise_base.append({
                    'name': name_field.value,
                    'muscle': muscle_field.value,
                    'description': desc_field.value,
                })
                save_data(data)
                page.pop_dialog()
                refresh_base_list()

            dialog = ft.AlertDialog(
                title=ft.Text('Новое упражнение'),
                content=ft.Column([name_field, muscle_field, desc_field], tight=True),
                actions=[
                    ft.TextButton('Добавить', on_click=save_new),
                    ft.TextButton('Отмена', on_click=lambda e: page.pop_dialog()),
                ],
            )
            page.show_dialog(dialog)
        base_list = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

        view = ft.View(
            route='/base',
            padding=0,
            controls=[
                ft.AppBar(
                    title=ft.Text('База упражнений'),
                    leading=ft.IconButton(
                        icon=ft.Icons.ARROW_BACK,
                        on_click=lambda e: asyncio.create_task(page.push_route("/")),
                    ),
                ),
                ft.Column(
                    controls=[
                        ft.Row(
                            [
                                ft.Text('Все упражнения', size=20, weight='bold'),
                                ft.Button('Добавить', on_click=open_add_exercise),
                            ],
                            alignment= ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Divider(),
                        base_list,
                    ],
                    expand=True,
                    spacing=10,
                ),
            ],
        )
        refresh_base_list()
        return view
 

    def build_muscle_picker_view(day_id):
        # Собираем уникальные группы мышц из базы
        muscles = sorted({ex.get('muscle', '') for ex in exercise_base if ex.get('muscle')})

        def go_to_muscle(e, m):
            asyncio.create_task(page.push_route(f"/add-to/{day_id}/{m}"))

        controls = [
            ft.AppBar(
                title=ft.Text("Выберите группу мышц"),
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
        rest_seconds = 30
        rest_task = None
        is_running = False

        ex_info = next((ex for ex in exercise_base if ex.get('name')==ex_name), None)
        image_src = ex_info.get('image') if ex_info else None

        def format_secs(sec):
            mins, s = divmod(int(sec), 60)
            return f"{mins:02d}:{s:02d}"

        def decrease_rest(e):
            nonlocal rest_seconds
            if is_running:
                return
            if rest_seconds > 30:
                rest_seconds -= 30
                rest_seconds_text.value = format_time(rest_seconds)
                page.update()

        def increase_rest(e):
            nonlocal rest_seconds
            if is_running:
                return
            rest_seconds += 30
            rest_seconds_text.value = format_time(rest_seconds)
            page.update()

        rest_seconds_text = ft.Text(f"{format_time(rest_seconds)}", size=24, weight='bold')
        rest_picker_row = ft.Row(
            controls=[
                ft.IconButton(icon=ft.Icons.REMOVE, on_click=decrease_rest, icon_size=20, visual_density=ft.VisualDensity.COMPACT),
                rest_seconds_text,
                ft.IconButton(icon=ft.Icons.ADD, on_click=increase_rest, icon_size=20, visual_density=ft.VisualDensity.COMPACT),
            ],
            alignment = ft.MainAxisAlignment.CENTER,
            spacing=5,
            tight=True
        )


        async def countdown():
            nonlocal rest_seconds, is_running
            is_running = True
            remaining = rest_seconds
            rest_seconds_text.value = format_time(remaining)
            page.update()

            while remaining > 0:
                rest_seconds_text.value = format_time(remaining)
                page.update()
                await asyncio.sleep(1)
                remaining -= 1

            rest_seconds_text.value = '00:00'
            await sound_fta.play()
            rest_seconds_text.value = format_time(rest_seconds)
            is_running = False
            page.update()


        def start_rest_timer():
            nonlocal rest_task, is_running
            if rest_task is not None:
                rest_task.cancel()
            is_running = False
            rest_task = page.run_task(countdown)


        def save_approach(e):
            import uuid
            # count = sum(1 for w in workouts if w.get('day_id') == day_id and w.get('exercise') == ex_name) + 1

            record = {
                'id': str(uuid.uuid4()),
                'day_id': day_id,
                'exercise': ex_name,
                'weight': weight_field.value,
                'reps': reps_field.value,
                'comment': comment_field.value,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'timestamp': datetime.now().isoformat(),
            }

            workouts.append(record)
            save_data(data)
            weight_field.value = ''
            reps_field.value = ''
            comment_field.value = ''
            update_stats_display()
            rebuild_history()
            start_rest_timer()

        def remove_approach(rec_id):
            for i, w in enumerate(workouts):
                if w.get('id') == rec_id:
                    del workouts[i]
                    break
            save_data(data)
            rebuild_history()

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
            count_text.value = f"Выполнено: {total}"

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

                    rec_id = w.get('id')

                    


                    # Функция заполнения полей по клику
                    def fill_fields(e, w=w):
                        weight_field.value = w.get('weight', '')
                        reps_field.value = w.get('reps', '')
                        comment_field.value = w.get('comment', '')
                        page.update()

                    row_content = ft.Row(
                                    controls=[
                                        ft.Text(f" #{num} {w.get('weight', '')} кг x {w.get('reps', '')} {comment_str}",
                                            size=14,
                                            expand=True,
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.START,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            )
                    
                    dismissible = ft.Dismissible(
                        content=ft.Container(
                            content=row_content,
                            on_click=fill_fields,
                            padding=ft.Padding.symmetric(horizontal=10, vertical=2),
                            height=25,
                        ),
                        dismiss_direction=ft.DismissDirection.END_TO_START,
                        background=ft.Container(
                            bgcolor=ft.Colors.RED,
                            alignment=ft.Alignment.CENTER_RIGHT,
                        ),
                        secondary_background=ft.Container(
                            content=ft.Icon(ft.Icons.DELETE, color=ft.Colors.WHITE, size=20),
                            bgcolor=ft.Colors.RED,
                            alignment=ft.Alignment.CENTER_RIGHT,
                            padding=ft.Padding.only(right=10),  # отступ только справа
                        ),
                        on_dismiss=lambda e, rid=rec_id: remove_approach(rid),
                        key=f"approach_{rec_id}",
                    )
                    history_column.controls.append(dismissible)

            page.update()

        # --- Поля ввода ---
        weight_field = ft.TextField(label='Вес (кг)', keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        reps_field = ft.TextField(label='Повторения', keyboard_type=ft.KeyboardType.NUMBER, expand=1)
        comment_field = ft.TextField(label='Комментарий', expand=2)
        count_text = ft.Text('Подходов выполнено: 0', size=16, weight='bold')
        history_column = ft.Column(spacing=5)

        add_button = ft.Button('Добавить подход', on_click=save_approach)

        # --- AppBar ---
        appbar = ft.AppBar(
            title=ft.Text(ex_name),
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                on_click=lambda e: asyncio.create_task(page.push_route("/")),
            ),
        )

        def open_image_fullscreen(src):
            def close_img(e):
                page.pop_dialog()

            dialog = ft.AlertDialog(
                content=ft.ListView(
                    controls=[
                        ft.Image(
                            src=src,
                            fit=ft.BoxFit.CONTAIN,
                            width=400,
                            height=400,
                    ),
                    ],
                    width=420,
                    height=420,
                ),
                actions=[ft.TextButton('Закрыть', on_click=close_img)],
            )
            page.show_dialog(dialog)

        # --- Содержимое ---
        content = ft.ListView(
            controls=[
                ft.GestureDetector(
                    on_tap=lambda e: open_image_fullscreen(image_src),
                    content=ft.Image(
                    src=image_src,
                    width=300,
                    height=200,
                    fit=ft.BoxFit.CONTAIN,
                    ),
                ) if image_src else ft.Container(),

                ft.Row([
                    rest_picker_row,
                    ft.Container(width=30),
                    count_text,
                ], alignment=ft.MainAxisAlignment.CENTER),
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
            # scroll=ft.ScrollMode.AUTO,
            expand=True
        )

        # --- Первая отрисовка истории ---
        rebuild_history()

        return ft.View(
            route=f"/exercise/{day_id}/{ex_name}",
            padding=0,
            controls=[appbar, content]
        )


    # --- Роутер ---
    def on_route_change(e):
        # page.views.clear()
        route = page.route
        view = None

        if route.startswith("/add-to/"):
            parts = route.split("/")
            day_id = parts[2]
            if len(parts) >= 4 and parts[3]:
                view = build_exercise_picker_view(day_id, parts[3])
            else:
                view = build_muscle_picker_view(day_id)
        elif route.startswith("/exercise/"):
            parts = route.split("/")
            day_id = parts[2]
            ex_name = parts[3]
            view = build_exercise_view(day_id, ex_name)
        elif route == "/base":
            view = build_base_view()
        else:
            view = build_main_view()
            refresh_exercises()
        # page.update()
        page.views.clear()
        page.views.append(view)
        page.update()

    page.on_route_change = on_route_change
    on_route_change(None)
    refresh_exercises()
    update_stats_display()
ft.run(main)