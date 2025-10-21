import flet as ft
import json
from datetime import datetime
import uuid


def main(page: ft.Page):
    page.title = "Сімейний бюджет"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT

    # --- Методи для роботи з даними ---
    def load_data():
        try:
            with open("budget_data.json", "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                "users": {
                    "user": {
                        "password": "pass",
                        "account_ids": ["default_main", "default_savings"]
                    }
                },
                "accounts": {
                    "default_main": {
                        "name": "Основний (приклад)",
                        "balance": 1500.0,
                        "transactions": [
                            {
                                "type": "income", "amount": 1500.0,
                                "description": "Початковий баланс",
                                "timestamp": datetime.now().isoformat(),
                                "user": "system"
                            }
                        ],
                        "owner": "user"
                    },
                    "default_savings": {
                        "name": "Заощадження (приклад)",
                        "balance": 5000.0,
                        "transactions": [
                            {
                                "type": "income", "amount": 5000.0,
                                "description": "Початковий баланс",
                                "timestamp": datetime.now().isoformat(),
                                "user": "system"
                            }
                        ],
                        "owner": "user"
                    }
                }
            }

    def save_data():
        with open("budget_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

    # Стан програми
    data = load_data()

    # Поля вводу
    username_field = ft.TextField(label="Ім'я користувача", width=300)
    password_field = ft.TextField(label="Пароль", password=True, can_reveal_password=True, width=300)
    login_error_text = ft.Text(value="", color='red')
    new_username_field = ft.TextField(label="Нове ім'я користувача", width=300)
    new_password_field = ft.TextField(label="Новий пароль", password=True, can_reveal_password=True, width=300)
    register_info_text = ft.Text(value="", width=300, text_align=ft.TextAlign.CENTER)
    account_name_field = ft.TextField(label="Назва рахунку", width=300, autofocus=True)
    join_link_field = ft.TextField(label="Вставте ID рахунку для приєднання", width=300)
    transaction_amount_field = ft.TextField(label="Сума", keyboard_type=ft.KeyboardType.NUMBER, width=300,
                                            autofocus=True)
    transaction_desc_field = ft.TextField(label="Опис / Коментар", width=300)
    transaction_error_text = ft.Text(value="", color="red")

    # --- Обробники подій ---
    def handle_login(e):
        username = username_field.value
        password = password_field.value
        if username in data["users"] and data["users"][username]["password"] == password:
            page.session.set("current_user", username)
            update_view()
        else:
            login_error_text.value = "Неправильне ім'я користувача або пароль"
            page.update()

    def handle_registration(e):
        username = new_username_field.value
        password = new_password_field.value

        MIN_PASSWORD_LENGTH = 8
        MIN_USERNAME_LENGTH = 2

        if not username or not password:
            register_info_text.value = "Ім'я та пароль не можуть бути порожніми."
            register_info_text.color = 'red'
        elif len(username) < MIN_USERNAME_LENGTH:
            register_info_text.value = f"Логін має бути не менше {MIN_USERNAME_LENGTH} символів."
            register_info_text.color = 'red'
        elif len(password) < MIN_PASSWORD_LENGTH:
            register_info_text.value = f"Пароль має бути не менше {MIN_PASSWORD_LENGTH} символів."
            register_info_text.color = 'red'
        elif username in data["users"]:
            register_info_text.value = f"Користувач '{username}' вже існує."
            register_info_text.color = 'red'
        else:
            data["users"][username] = {"password": password, "account_ids": []}
            save_data()
            register_info_text.value = "Реєстрація успішна! Тепер ви можете увійти."
            register_info_text.color = 'green'
            new_username_field.value = ""
            new_password_field.value = ""
        page.update()

    def handle_logout(e):
        page.session.set("current_user", None)
        go_to_view("login")

    def add_transaction_logic(account_id, trans_type, amount, description, user_who_added):
        account = data["accounts"].get(account_id)
        if not account: return

        if trans_type == "income":
            account["balance"] += amount
        else:
            account["balance"] -= amount

        account["transactions"].append({
            "type": trans_type, "amount": amount,
            "description": description, "timestamp": datetime.now().isoformat(),
            "user": user_who_added
        })
        save_data()

    def handle_add_transaction(e):
        transaction_error_text.value = ""
        trans_type = page.session.get("transaction_type")
        current_user = page.session.get("current_user")
        account_id = page.session.get("current_account_id")

        try:
            amount = float(transaction_amount_field.value)
            description = transaction_desc_field.value.strip() or (
                "Дохід" if trans_type == "income" else "Витрата"
            )
            add_transaction_logic(account_id, trans_type, amount, description, current_user)
            transaction_amount_field.value = ""
            transaction_desc_field.value = ""
            go_to_view("account_details")

        except (ValueError, TypeError):
            print("Неправильна сума")
            transaction_error_text.value = "Сума має бути числом (наприклад: 150.50)"
            page.update()

    def handle_add_account(e):
        name = account_name_field.value.strip()
        current_user = page.session.get("current_user")
        user = data["users"][current_user]

        if name and len(user["account_ids"]) < 4:
            new_id = str(uuid.uuid4())
            data["accounts"][new_id] = {
                "name": name,
                "balance": 0.0,
                "transactions": [],
                "owner": current_user
            }
            user["account_ids"].append(new_id)
            save_data()
            account_name_field.value = ""
            go_to_view(None)

    def handle_join_account(e):
        account_id_to_join = join_link_field.value.strip()
        current_user = page.session.get("current_user")
        user = data["users"][current_user]

        if account_id_to_join not in data["accounts"]:
            print(f"Помилка: Рахунок з ID {account_id_to_join} не знайдено.")
            return
        if len(user["account_ids"]) >= 4:
            print(f"Помилка: Ви досягли ліміту в 4 рахунки.")
            return
        if account_id_to_join in user["account_ids"]:
            print(f"Помилка: Рахунок вже у вашому списку.")
            return

        user["account_ids"].append(account_id_to_join)
        save_data()

        print(f"Рахунок {account_id_to_join} успішно додано!")
        join_link_field.value = ""
        go_to_view(None)

        # --- НОВА ФУНКЦІЯ: Логіка видалення ---

    def handle_delete_account(e):
        account_id = page.session.get("current_account_id")
        if not account_id:
            go_to_view(None)
            return

        # 1. Видаляємо ID рахунку з усіх користувачів
        for username, user_data in data["users"].items():
            if account_id in user_data["account_ids"]:
                user_data["account_ids"].remove(account_id)

        # 2. Видаляємо сам рахунок
        if account_id in data["accounts"]:
            del data["accounts"][account_id]

        save_data()
        go_to_view(None)  # Повертаємось на головну

    # --- Навігація ---
    def go_to_view(view_name):
        page.session.set("view", view_name)
        login_error_text.value = ""
        register_info_text.value = ""
        transaction_error_text.value = ""
        update_view()

    def open_account_details(account_id):
        page.session.set("current_account_id", account_id)
        go_to_view("account_details")

    def open_transaction_page(trans_type):
        page.session.set("transaction_type", trans_type)
        go_to_view("add_transaction")

    # --- Функції для побудови інтерфейсу (Views) ---
    def build_login_view():
        return ft.Column(
            [
                ft.Text("Вхід до системи", size=32, weight=ft.FontWeight.BOLD),
                username_field, password_field,
                ft.ElevatedButton("Увійти", on_click=handle_login),
                login_error_text,
                ft.TextButton("Немає акаунту? Зареєструватися", on_click=lambda e: go_to_view("register"))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20
        )

    def build_register_view():
        return ft.Column(
            [
                ft.Text("Реєстрація", size=32, weight=ft.FontWeight.BOLD),
                new_username_field, new_password_field,
                ft.ElevatedButton("Зареєструватися", on_click=handle_registration),
                register_info_text,
                ft.TextButton("Вже є акаунт? Увійти", on_click=lambda e: go_to_view("login"))
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=20
        )

    def build_add_account_view():
        return ft.Column(
            [
                ft.Row([
                    ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: go_to_view(None), tooltip="Назад"),
                    ft.Container(expand=True)
                ]),

                ft.Text("Створення нового рахунку", size=20, weight=ft.FontWeight.BOLD),
                account_name_field,
                ft.Row(
                    [ft.FilledButton("Створити рахунок", on_click=handle_add_account)],
                    alignment=ft.MainAxisAlignment.END
                ),

                ft.Divider(height=30, thickness=2),

                ft.Text("Або приєднатися за ID", size=18, weight=ft.FontWeight.BOLD),
                join_link_field,
                ft.Row(
                    [ft.FilledButton("Приєднатися", on_click=handle_join_account)],
                    alignment=ft.MainAxisAlignment.END
                )
            ],
            width=800, spacing=20
        )

    def build_account_details_view():
        account_id = page.session.get("current_account_id")
        account = data["accounts"].get(account_id)

        if account is None:
            go_to_view(None);
            return ft.Container()

        # --- НОВІ ЕЛЕМЕНТИ для перейменування ---
        rename_account_field = ft.TextField(label="Змінити назву", value=account["name"])

        def handle_rename(e):
            new_name = rename_account_field.value.strip()
            if new_name:
                account["name"] = new_name
                save_data()
                update_view()  # Оновлюємо сторінку, щоб побачити зміни

        left_column = ft.Column(
            [
                ft.Text("Поточний баланс:", size=16, color="grey"),
                ft.Text(f"{account['balance']:.2f} грн", size=32, weight=ft.FontWeight.BOLD),
                ft.Divider(height=10),

                ft.Text("Операції:", size=18),
                ft.ElevatedButton("Додати дохід", icon=ft.Icons.ADD, on_click=lambda e: open_transaction_page("income"),
                                  expand=True),
                ft.ElevatedButton("Додати витрату", icon=ft.Icons.REMOVE,
                                  on_click=lambda e: open_transaction_page("expense"), expand=True),

                ft.Divider(height=10),

                ft.Text("Спільний доступ:", size=18),
                ft.TextField(label="ID для запрошення (скопіюйте це)", value=f"{account_id}", read_only=True),
                ft.Text(f"Власник: {account['owner']}", size=12, color="grey", italic=True),

                ft.Divider(height=10),

                # --- НОВИЙ БЛОК: Керування ---
                ft.Text("Керування рахунком:", size=18),
                rename_account_field,
                ft.ElevatedButton("Перейменувати", icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE, on_click=handle_rename),
                ft.ElevatedButton("Видалити рахунок", icon=ft.Icons.DELETE_FOREVER,
                                  on_click=lambda e: go_to_view("delete_account")),

            ],
            width=350,
            spacing=10
        )

        transactions_list = ft.ListView(spacing=5, height=600, expand=True)  # Збільшив висоту
        if not account["transactions"]:
            transactions_list.controls.append(ft.Text("Історія транзакцій порожня."))
        else:
            sorted_transactions = sorted(account["transactions"], key=lambda x: x["timestamp"], reverse=True)
            for t in sorted_transactions:
                timestamp_str = datetime.fromisoformat(t['timestamp']).strftime('%Y-%m-%d %H:%M')
                user_str = t.get('user', 'невідомо')

                transactions_list.controls.append(ft.ListTile(
                    leading=ft.Icon(ft.Icons.ARROW_UPWARD if t["type"] == "income" else ft.Icons.ARROW_DOWNWARD,
                                    color='green' if t["type"] == "income" else 'red'),
                    title=ft.Text(t['description']),
                    subtitle=ft.Text(f"{timestamp_str} - {user_str}"),
                    trailing=ft.Text(f"{'+' if t['type'] == 'income' else '-'}{t['amount']:.2f} грн",
                                     weight=ft.FontWeight.BOLD)
                ))

        right_column = ft.Column(
            [
                ft.Text("Історія транзакцій:", size=18),
                transactions_list
            ],
            width=430
        )

        return ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: go_to_view(None), tooltip="Назад"),
                ft.Text(account["name"], size=24, weight=ft.FontWeight.BOLD, expand=True),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Divider(height=10),
            ft.Row([left_column, right_column], spacing=20, vertical_alignment=ft.CrossAxisAlignment.START)
        ], width=800, spacing=10)

    def build_add_transaction_view():
        account_id = page.session.get("current_account_id")
        account = data["accounts"].get(account_id)
        trans_type = page.session.get("transaction_type")
        title = "Додати дохід" if trans_type == "income" else "Додати витрату"

        return ft.Column([
            ft.Row([
                ft.IconButton(ft.Icons.ARROW_BACK, on_click=lambda e: go_to_view("account_details"), tooltip="Назад"),
                ft.Container(expand=True),
            ]),
            ft.Text(f'{title} до "{account["name"]}"', size=20, weight=ft.FontWeight.BOLD),
            transaction_amount_field,
            transaction_desc_field,
            transaction_error_text,
            ft.Row(
                [
                    ft.TextButton("Скасувати", on_click=lambda e: go_to_view("account_details")),
                    ft.FilledButton("Додати", on_click=handle_add_transaction)
                ],
                alignment=ft.MainAxisAlignment.END
            )
        ], width=800, spacing=20)

    # --- НОВА СТОРІНКА: Підтвердження видалення ---
    def build_delete_confirmation_view():
        account_id = page.session.get("current_account_id")
        account = data["accounts"].get(account_id)

        if account is None:
            go_to_view(None);
            return ft.Container()

        return ft.Column(
            [
                ft.Text("Видалити рахунок?", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Ви впевнені, що хочете видалити рахунок '{account['name']}'?",
                        text_align=ft.TextAlign.CENTER),
                ft.Text(f"Усі транзакції та баланс ({account['balance']:.2f} грн) будуть видалені НАЗАВЖДИ.",
                        text_align=ft.TextAlign.CENTER, color="red", weight=ft.FontWeight.BOLD),
                ft.Text("Ця дія незворотня.", text_align=ft.TextAlign.CENTER),
                ft.Row(
                    [
                        ft.TextButton("Скасувати", on_click=lambda e: go_to_view("account_details")),
                        ft.FilledButton("Так, видалити", on_click=handle_delete_account)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                )
            ],
            width=800, spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

    def build_main_view():
        current_user = page.session.get("current_user")
        user_account_ids = data["users"][current_user]["account_ids"]
        accounts = [data["accounts"].get(acc_id) for acc_id in user_account_ids if data["accounts"].get(acc_id)]

        header = ft.Row([
            ft.Text(f"Вітаємо, {current_user}!", size=24, weight=ft.FontWeight.BOLD, expand=True),
            ft.IconButton(ft.Icons.LOGOUT, on_click=handle_logout, tooltip="Вийти")
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        if not accounts:
            return ft.Column([
                header,
                ft.Container(
                    ft.Column([
                        ft.Text("Ласкаво просимо до вашого бюджету!", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text("Наразі у вас немає жодного рахунку. Створіть перший або приєднайтесь до існуючого.",
                                text_align=ft.TextAlign.CENTER),
                        ft.ElevatedButton("Додати/Створити рахунок", icon=ft.Icons.ADD,
                                          on_click=lambda e: go_to_view("add_account")),
                    ], spacing=15, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=40, border_radius=10, border=ft.border.all(1, 'grey'),
                    margin=ft.margin.only(top=20)
                )
            ], width=800, spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        else:
            account_cards = []
            for i, acc in enumerate(accounts):
                acc_id = user_account_ids[i]
                card = ft.Container(
                    content=ft.Column([
                        ft.Text(acc["name"], size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{acc['balance']:.2f} грн", size=20),
                    ]),
                    padding=15,
                    width=220,
                    border_radius=10,
                    border=ft.border.all(1, 'grey'),
                    on_click=(lambda id=acc_id: lambda e: open_account_details(id))(),
                )
                account_cards.append(card)

            all_transactions = []
            for acc_id in user_account_ids:
                account = data["accounts"].get(acc_id)
                if not account: continue
                for t in account["transactions"]:
                    all_transactions.append({**t, "account_name": account["name"]})
            all_transactions.sort(key=lambda x: x["timestamp"], reverse=True)

            transactions_list = ft.ListView(spacing=5, height=200, expand=True)
            if not all_transactions:
                transactions_list.controls.append(ft.Text("Історія транзакцій порожня."))
            else:
                for t in all_transactions[:10]:
                    timestamp_str = datetime.fromisoformat(t['timestamp']).strftime('%Y-%m-%d %H:%M')
                    user_str = t.get('user', 'невідомо')

                    transactions_list.controls.append(ft.ListTile(
                        leading=ft.Icon(ft.Icons.ARROW_UPWARD if t["type"] == "income" else ft.Icons.ARROW_DOWNWARD,
                                        color='green' if t["type"] == "income" else 'red'),
                        title=ft.Text(f"{t['description']} ({t['account_name']})"),
                        subtitle=ft.Text(f"{timestamp_str} - {user_str}"),
                        trailing=ft.Text(f"{'+' if t['type'] == 'income' else '-'}{t['amount']:.2f} грн",
                                         weight=ft.FontWeight.BOLD)
                    ))

            return ft.Column([
                header,
                ft.Text("Ваші рахунки:", size=18),
                ft.Row(controls=account_cards, wrap=True, spacing=20, run_spacing=20),
                ft.ElevatedButton("Додати рахунок", icon=ft.Icons.ADD, on_click=lambda e: go_to_view("add_account"),
                                  disabled=len(accounts) >= 4),
                ft.Divider(height=20),
                ft.Text("Останні транзакції (всі рахунки):", size=18),
                transactions_list
            ], width=800, spacing=20)

    # --- Головна функція оновлення вигляду ---
    def update_view():
        page.clean()
        current_user = page.session.get("current_user")
        current_view = page.session.get("view")

        if not current_user:
            if current_view == "register":
                page.add(build_register_view())
            else:
                page.add(build_login_view())
        else:
            if current_view == "add_account":
                page.add(build_add_account_view())
            elif current_view == "account_details":
                page.add(build_account_details_view())
            elif current_view == "add_transaction":
                page.add(build_add_transaction_view())
            elif current_view == "delete_account":  # <-- НОВА СТОРІНКА
                page.add(build_delete_confirmation_view())
            else:
                page.add(build_main_view())

        page.update()

    if not page.session.get("view"):
        page.session.set("view", "login")

    update_view()


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)