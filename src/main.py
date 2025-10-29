import flet as ft
import sqlite3
from datetime import datetime
import uuid

# Файл БД буде створено в папці src, бо тут знаходиться і головний файл
DB_FILE = "budget.db"


def get_db_conn():
    """Створює нове підключення до БД. Це безпечно для потоків Flet."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Ініціалізує БД та створює таблиці, якщо вони не існують."""
    with get_db_conn() as conn:
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts (
                account_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                balance REAL NOT NULL,
                owner_username TEXT NOT NULL,
                FOREIGN KEY (owner_username) REFERENCES users (username)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_accounts_link (
                username TEXT NOT NULL,
                account_id TEXT NOT NULL,
                PRIMARY KEY (username, account_id),
                FOREIGN KEY (username) REFERENCES users (username),
                FOREIGN KEY (account_id) REFERENCES accounts (account_id)
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id TEXT NOT NULL,
                type TEXT NOT NULL,
                amount REAL NOT NULL,
                description TEXT,
                timestamp TEXT NOT NULL,
                user_username TEXT NOT NULL,
                FOREIGN KEY (account_id) REFERENCES accounts (account_id),
                FOREIGN KEY (user_username) REFERENCES users (username)
            )
        """)

        try:
            c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ("user", "pass"))
        except sqlite3.IntegrityError:
            pass

        conn.commit()


def main(page: ft.Page):
    page.title = "Сімейний бюджет"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER
    page.theme_mode = ft.ThemeMode.LIGHT

    init_db()

    # поля для вводу даних
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
    add_account_error_text = ft.Text(value="", color="red")

    def handle_login(e):
        username = username_field.value
        password = password_field.value
        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT password FROM users WHERE username = ?", (username,))
            user_data = c.fetchone()

        if user_data and user_data["password"] == password:
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
        else:
            with get_db_conn() as conn:
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE username = ?", (username,))
                if c.fetchone():
                    register_info_text.value = f"Користувач '{username}' вже існує."
                    register_info_text.color = 'red'
                else:
                    c.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                    conn.commit()
                    register_info_text.value = "Реєстрація успішна! Тепер ви можете увійти."
                    register_info_text.color = 'green'
                    new_username_field.value = ""
                    new_password_field.value = ""
        page.update()

    def handle_logout(e):
        page.session.set("current_user", None)
        go_to_view("login")

    def add_transaction_logic(account_id, trans_type, amount, description, user_who_added):
        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("""
                INSERT INTO transactions (account_id, type, amount, description, timestamp, user_username)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (account_id, trans_type, amount, description, datetime.now().isoformat(), user_who_added))

            update_amount = amount if trans_type == "income" else -amount
            c.execute("""
                UPDATE accounts
                SET balance = balance + ?
                WHERE account_id = ?
            """, (update_amount, account_id))

            conn.commit()

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
        add_account_error_text.value = ""
        page.update()

        name = account_name_field.value.strip()
        current_user = page.session.get("current_user")

        # --- ОСЬ ТУТ ЗМІНИ ---
        if not name:
            add_account_error_text.value = "Назва рахунку не може бути порожньою."
            page.update()
            return

        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM user_accounts_link WHERE username = ?", (current_user,))
            count = c.fetchone()[0]

            if count >= 4:
                add_account_error_text.value = "Ви досягли ліміту в 4 рахунки."
                page.update()
                return

            new_id = str(uuid.uuid4())
            c.execute("""
                INSERT INTO accounts (account_id, name, balance, owner_username)
                VALUES (?, ?, 0.0, ?)
            """, (new_id, name, current_user))
            c.execute("""
                INSERT INTO user_accounts_link (username, account_id)
                VALUES (?, ?)
            """, (current_user, new_id))
            conn.commit()
            account_name_field.value = ""
            go_to_view(None)

    def handle_join_account(e):
        account_id_to_join = join_link_field.value.strip()
        current_user = page.session.get("current_user")

        with get_db_conn() as conn:
            c = conn.cursor()

            c.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id_to_join,))
            if not c.fetchone():
                print(f"Помилка: Рахунок з ID {account_id_to_join} не знайдено.")
                return

            c.execute("SELECT COUNT(*) FROM user_accounts_link WHERE username = ?", (current_user,))
            if c.fetchone()[0] >= 4:
                print(f"Помилка: Ви досягли ліміту в 4 рахунки.")
                return

            c.execute("SELECT * FROM user_accounts_link WHERE username = ? AND account_id = ?",
                      (current_user, account_id_to_join))
            if c.fetchone():
                print(f"Помилка: Рахунок вже у вашому списку.")
                return

            c.execute("INSERT INTO user_accounts_link (username, account_id) VALUES (?, ?)",
                      (current_user, account_id_to_join))
            conn.commit()

            print(f"Рахунок {account_id_to_join} успішно додано!")
            join_link_field.value = ""
            go_to_view(None)

    def handle_delete_account(e):
        account_id = page.session.get("current_account_id")
        current_user = page.session.get("current_user")
        if not account_id:
            go_to_view(None)
            return

        with get_db_conn() as conn:
            c = conn.cursor()

            c.execute("SELECT owner_username FROM accounts WHERE account_id = ?", (account_id,))
            account_data = c.fetchone()

            if account_data and account_data["owner_username"] == current_user:
                print("Ви власник. Видалення рахунку...")
                # 2a. Видаляємо всі зв'язки
                c.execute("DELETE FROM user_accounts_link WHERE account_id = ?", (account_id,))
                # 2b. Видаляємо всі транзакції
                c.execute("DELETE FROM transactions WHERE account_id = ?", (account_id,))
                # 2c. Видаляємо сам рахунок
                c.execute("DELETE FROM accounts WHERE account_id = ?", (account_id,))
            else:
                print("Ви не власник. Вихід з рахунку...")
                c.execute("DELETE FROM user_accounts_link WHERE username = ? AND account_id = ?",
                          (current_user, account_id))

            conn.commit()

        go_to_view(None)

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
                add_account_error_text,
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
            width=800, spacing=15
        )

    def build_account_details_view():
        account_id = page.session.get("current_account_id")
        current_user = page.session.get("current_user")

        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,))
            account = c.fetchone()
            c.execute("SELECT * FROM transactions WHERE account_id = ? ORDER BY timestamp DESC", (account_id,))
            transactions = c.fetchall()

        if account is None:
            go_to_view(None);
            return ft.Container()

        rename_account_field = ft.TextField(label="Змінити назву", value=account["name"])

        def handle_rename(e):
            new_name = rename_account_field.value.strip()
            if new_name:
                with get_db_conn() as conn:
                    conn.execute("UPDATE accounts SET name = ? WHERE account_id = ?", (new_name, account_id))
                    conn.commit()
                update_view()


        is_owner = (account["owner_username"] == current_user)

        delete_button_text = "Видалити рахунок (Ви Власник)" if is_owner else "Покинути рахунок"
        delete_button_icon = ft.Icons.DELETE_FOREVER if is_owner else ft.Icons.LOGOUT

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
                ft.Text(f"Власник: {account['owner_username']}", size=12, color="grey", italic=True),
                ft.Divider(height=10),
                ft.Text("Керування рахунком:", size=18),
                rename_account_field,
                ft.ElevatedButton("Перейменувати", icon=ft.Icons.DRIVE_FILE_RENAME_OUTLINE, on_click=handle_rename),
                ft.ElevatedButton(delete_button_text, icon=delete_button_icon,
                                  on_click=lambda e: go_to_view("delete_account")),
            ],
            width=350,
            spacing=10
        )

        transactions_list = ft.ListView(spacing=5, height=600, expand=True)
        if not transactions:
            transactions_list.controls.append(ft.Text("Історія транзакцій порожня."))
        else:
            for t in transactions:
                timestamp_str = datetime.fromisoformat(t['timestamp']).strftime('%Y-%m-%d %H:%M')
                user_str = t['user_username']

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

        with get_db_conn() as conn:
            account = conn.execute("SELECT name FROM accounts WHERE account_id = ?", (account_id,)).fetchone()

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

    def build_delete_confirmation_view():
        account_id = page.session.get("current_account_id")
        current_user = page.session.get("current_user")

        with get_db_conn() as conn:
            account = conn.execute("SELECT * FROM accounts WHERE account_id = ?", (account_id,)).fetchone()

        if account is None:
            go_to_view(None);
            return ft.Container()

        is_owner = (account["owner_username"] == current_user)

        if is_owner:
            title_text = "Видалити рахунок?"
            warning_text = f"Усі транзакції та баланс ({account['balance']:.2f} грн) будуть видалені НАЗАВЖДИ."
            button_text = "Так, видалити"
        else:
            title_text = "Покинути рахунок?"
            warning_text = "Ви втратите доступ до цього рахунку, але він залишиться в інших учасників."
            button_text = "Так, покинути"

        return ft.Column(
            [
                ft.Text(title_text, size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Ви впевнені, що хочете це зробити з рахунком '{account['name']}'?",
                        text_align=ft.TextAlign.CENTER),
                ft.Text(warning_text, text_align=ft.TextAlign.CENTER, color="red", weight=ft.FontWeight.BOLD),
                ft.Text("Ця дія незворотня.", text_align=ft.TextAlign.CENTER),
                ft.Row(
                    [
                        ft.TextButton("Скасувати", on_click=lambda e: go_to_view("account_details")),
                        ft.FilledButton(button_text, on_click=handle_delete_account)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=20
                )
            ],
            width=800, spacing=20, horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )

    def build_main_view():
        current_user = page.session.get("current_user")

        with get_db_conn() as conn:
            c = conn.cursor()
            c.execute("SELECT account_id FROM user_accounts_link WHERE username = ?", (current_user,))
            user_account_ids_tuples = c.fetchall()
            user_account_ids = [row["account_id"] for row in user_account_ids_tuples]

            accounts = []
            if user_account_ids:
                # цікавий момент, пов'язаний зі створенням плейсхолдерів '?' для запиту
                placeholders = ','.join('?' for _ in user_account_ids)
                c.execute(f"SELECT * FROM accounts WHERE account_id IN ({placeholders})", user_account_ids)
                accounts = c.fetchall()

            all_transactions = []
            if user_account_ids:
                c.execute(f"""
                    SELECT t.*, a.name as account_name FROM transactions t
                    JOIN accounts a ON t.account_id = a.account_id
                    WHERE t.account_id IN ({placeholders})
                    ORDER BY t.timestamp DESC
                    LIMIT 10
                """, user_account_ids)
                all_transactions = c.fetchall()

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
            for acc in accounts:
                card = ft.Container(
                    content=ft.Column([
                        ft.Text(acc["name"], size=16, weight=ft.FontWeight.BOLD),
                        ft.Text(f"{acc['balance']:.2f} грн", size=20),
                    ]),
                    padding=15,
                    width=220,
                    border_radius=10,
                    border=ft.border.all(1, 'grey'),
                    on_click=(lambda id=acc["account_id"]: lambda e: open_account_details(id))(),
                )
                account_cards.append(card)

            transactions_list = ft.ListView(spacing=5, height=200, expand=True)
            if not all_transactions:
                transactions_list.controls.append(ft.Text("Історія транзакцій порожня."))
            else:
                for t in all_transactions:
                    timestamp_str = datetime.fromisoformat(t['timestamp']).strftime('%Y-%m-%d %H:%M')
                    user_str = t['user_username']

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
            elif current_view == "delete_account":
                page.add(build_delete_confirmation_view())
            else:
                page.add(build_main_view())

        page.update()

    if not page.session.get("view"):
        page.session.set("view", "login")

    update_view()


if __name__ == "__main__":
    ft.app(target=main, view=ft.AppView.WEB_BROWSER)