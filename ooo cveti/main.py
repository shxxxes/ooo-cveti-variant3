
from __future__ import annotations

import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path
from typing import Optional

from db import (
    APP_ROOT,
    ASSETS_PRODUCTS_DIR,
    AuthUser,
    authenticate,
    get_conn,
    init_db_if_needed,
)

try:
    from PIL import Image, ImageTk
except Exception:
    Image = None
    ImageTk = None


PLACEHOLDER_IMG = APP_ROOT / "assets" / "ui" / "picture.png"

print('База данных ипортирована.')

def discounted_price(cost: float, discount: int) -> float:
    return round(cost * (1 - discount / 100.0), 2)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("ООО «Цветы»")
        self.geometry("1200x650")
        self.minsize(980, 600)

        self.current_user: Optional[AuthUser] = None

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)

        self.frames: dict[type[ttk.Frame], ttk.Frame] = {}
        for F in (LoginPage, ProductListPage, ProductEditPage, OrdersPage, OrderEditPage):
            frame = F(parent=container, app=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show(LoginPage)

    def show(self, frame_cls: type[ttk.Frame]) -> None:
        frame = self.frames[frame_cls]
        if hasattr(frame, "on_show"):
            frame.on_show()
        frame.tkraise()

    def logout(self) -> None:
        self.current_user = None
        self.show(LoginPage)


class TopBar(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: App, title: str):
        super().__init__(parent)
        self.app = app
        self.columnconfigure(0, weight=1)
        self.lbl_title = ttk.Label(self, text=title, font=("Segoe UI", 14, "bold"))
        self.lbl_title.grid(row=0, column=0, sticky="w", padx=10, pady=10)

        self.lbl_user = ttk.Label(self, text="", font=("Segoe UI", 10))
        self.lbl_user.grid(row=0, column=1, sticky="e", padx=10)

        self.btn_logout = ttk.Button(self, text="Выйти", command=self.app.logout)
        self.btn_logout.grid(row=0, column=2, sticky="e", padx=10)

    def refresh_user(self) -> None:
        if self.app.current_user:
            self.lbl_user.config(text=f"{self.app.current_user.fio} ({self.app.current_user.role})")
            self.btn_logout.state(["!disabled"])
        else:
            self.lbl_user.config(text="Гость")
            self.btn_logout.state(["disabled"])


class LoginPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: App):
        super().__init__(parent)
        self.app = app

        wrap = ttk.Frame(self)
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ttk.Label(wrap, text="Вход в систему", font=("Segoe UI", 16, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 15))

        ttk.Label(wrap, text="Логин:").grid(row=1, column=0, sticky="e", padx=5, pady=5)
        ttk.Label(wrap, text="Пароль:").grid(row=2, column=0, sticky="e", padx=5, pady=5)

        self.var_login = tk.StringVar()
        self.var_pass = tk.StringVar()

        ent_login = ttk.Entry(wrap, width=35, textvariable=self.var_login)
        ent_pass = ttk.Entry(wrap, width=35, textvariable=self.var_pass, show="*")
        ent_login.grid(row=1, column=1, padx=5, pady=5)
        ent_pass.grid(row=2, column=1, padx=5, pady=5)

        ttk.Button(wrap, text="Войти", command=self.do_login).grid(row=3, column=0, columnspan=2, pady=(10, 0), sticky="ew")
        ttk.Button(wrap, text="Продолжить как гость", command=self.go_guest).grid(row=4, column=0, columnspan=2, pady=8, sticky="ew")

        ent_login.focus_set()

    def do_login(self) -> None:
        user = authenticate(self.var_login.get(), self.var_pass.get())
        if not user:
            messagebox.showerror("Ошибка авторизации", "Неверный логин или пароль.")
            return
        self.app.current_user = user
        self.app.show(ProductListPage)

    def go_guest(self) -> None:
        self.app.current_user = None
        self.app.show(ProductListPage)


class ProductListPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: App):
        super().__init__(parent)
        self.app = app

        self.top = TopBar(self, app, "Товары")
        self.top.pack(fill="x")

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=5)

        ttk.Label(controls, text="Поиск:").grid(row=0, column=0, sticky="w")
        self.var_search = tk.StringVar()
        ent_search = ttk.Entry(controls, textvariable=self.var_search, width=35)
        ent_search.grid(row=0, column=1, padx=6)

        ttk.Label(controls, text="Поставщик:").grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.var_supplier = tk.StringVar(value="Все поставщики")
        self.cmb_supplier = ttk.Combobox(controls, textvariable=self.var_supplier, width=28, state="readonly")
        self.cmb_supplier.grid(row=0, column=3, padx=6)

        ttk.Label(controls, text="Сортировка по остатку:").grid(row=0, column=4, sticky="w", padx=(10, 0))
        self.var_sort = tk.StringVar(value="без сортировки")
        self.cmb_sort = ttk.Combobox(controls, textvariable=self.var_sort, width=18, state="readonly",
                                     values=["без сортировки", "по возрастанию", "по убыванию"])
        self.cmb_sort.grid(row=0, column=5, padx=6)

        self.btn_add = ttk.Button(controls, text="Добавить товар", command=self.add_product)
        self.btn_add.grid(row=0, column=6, padx=(10, 0))

        self.btn_import = ttk.Button(controls, text="Импорт", command=self.fake_import)
        self.btn_import.grid(row=0, column=8, padx=6)

        self.btn_orders = ttk.Button(controls, text="Заказы", command=lambda: self.app.show(OrdersPage))
        self.btn_orders.grid(row=0, column=7, padx=6)

        self.tree = ttk.Treeview(
            self,
            columns=("article", "name", "category", "supplier", "cost", "disc", "final", "qty"),
            show="headings",
            height=20,
        )
        for col, title, w in [
            ("article", "Артикул", 90),
            ("name", "Наименование", 220),
            ("category", "Категория", 120),
            ("supplier", "Поставщик", 140),
            ("cost", "Цена", 80),
            ("disc", "Скидка %", 80),
            ("final", "Цена со скидкой", 120),
            ("qty", "Остаток", 80),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        # Row tags for highlight
        self.tree.tag_configure("big_discount", background="#2E8B57")
        self.tree.tag_configure("out_of_stock", background="#87CEFA")  # light blue

        # reactive updates
        self.var_search.trace_add("write", lambda *_: self.refresh())
        self.var_supplier.trace_add("write", lambda *_: self.refresh())
        self.var_sort.trace_add("write", lambda *_: self.refresh())

        self.tree.bind("<Double-1>", self.open_for_edit)

    def fake_import(self) -> None:
        role = self.app.current_user.role if self.app.current_user else "Гость"
        if role != "Администратор":
            messagebox.showwarning("Доступ запрещён", "Импорт доступен только Администратору.")
            return

        path = filedialog.askopenfilename(
            title="Выберите файл для импорта",
            filetypes=[("Excel files", "*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        # Заглушка: реальный импорт не выполняем
        messagebox.showinfo("Импорт", f"Файл выбран:\n{path}\n\nИмпорт выполнен успешно (заглушка).")

    def on_show(self) -> None:
        self.top.refresh_user()
        role = self.app.current_user.role if self.app.current_user else "Гость"

        # permissions
        if role == "Администратор":
            self.btn_add.state(["!disabled"])
            self.btn_orders.state(["!disabled"])
            self.btn_import.state(["!disabled"])
        elif role == "Менеджер":
            self.btn_add.state(["disabled"])
            self.btn_orders.state(["!disabled"])
        else:
            self.btn_add.state(["disabled"])
            self.btn_orders.state(["disabled"])
            self.btn_import.state(["disabled"])

        # suppliers list
        with get_conn() as conn:
            rows = conn.execute("SELECT DISTINCT supplier FROM product ORDER BY supplier").fetchall()
        values = ["Все поставщики"] + [r["supplier"] for r in rows]
        self.cmb_supplier["values"] = values
        if self.var_supplier.get() not in values:
            self.var_supplier.set("Все поставщики")

        self.refresh()

    def _query_products(self):
        search = self.var_search.get().strip().lower()
        supplier = self.var_supplier.get().strip()
        sort = self.var_sort.get()

        where = []
        params = []

        if supplier and supplier != "Все поставщики":
            where.append("supplier = ?")
            params.append(supplier)

        if search:
            like = f"%{search}%"
            where.append("(lower(article) LIKE ? OR lower(name) LIKE ? OR lower(description) LIKE ? OR lower(category) LIKE ? OR lower(manufacturer) LIKE ? OR lower(supplier) LIKE ?)")
            params.extend([like, like, like, like, like, like])

        order_by = ""
        if sort == "по возрастанию":
            order_by = "ORDER BY quantity ASC"
        elif sort == "по убыванию":
            order_by = "ORDER BY quantity DESC"

        where_sql = ("WHERE " + " AND ".join(where)) if where else ""
        sql = f"""
            SELECT article, name, category, supplier, cost, discount, quantity
            FROM product
            {where_sql}
            {order_by}
        """

        with get_conn() as conn:
            return conn.execute(sql, params).fetchall()

    def refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)

        rows = self._query_products()
        for r in rows:
            cost = float(r["cost"])
            disc = int(r["discount"])
            qty = int(r["quantity"])
            final = discounted_price(cost, disc) if disc > 0 else cost
            tags = []
            if qty == 0:
                tags.append("out_of_stock")
            if disc > 15:
                tags.append("big_discount")
            self.tree.insert(
                "",
                "end",
                iid=r["article"],
                values=(r["article"], r["name"], r["category"], r["supplier"], f"{cost:.2f}", f"{disc}", f"{final:.2f}", qty),
                tags=tags,
            )

    def _require_admin(self) -> bool:
        role = self.app.current_user.role if self.app.current_user else "Гость"
        if role != "Администратор":
            messagebox.showwarning("Доступ запрещён", "Действие доступно только Администратору.")
            return False
        return True

    def add_product(self) -> None:
        if not self._require_admin():
            return
        edit_page: ProductEditPage = self.app.frames[ProductEditPage]  # type: ignore[assignment]
        edit_page.set_product(article=None)
        self.app.show(ProductEditPage)

    def open_for_edit(self, _evt=None) -> None:
        if not self._require_admin():
            return
        sel = self.tree.selection()
        if not sel:
            return
        article = sel[0]
        edit_page: ProductEditPage = self.app.frames[ProductEditPage]  # type: ignore[assignment]
        edit_page.set_product(article=article)
        self.app.show(ProductEditPage)


class ProductEditPage(ttk.Frame):
    _open_lock = False  # prevent multiple edit windows (within the app)

    def __init__(self, parent: ttk.Frame, app: App):
        super().__init__(parent)
        self.app = app
        self.top = TopBar(self, app, "Товар — добавление/редактирование")
        self.top.pack(fill="x")

        self.article: Optional[str] = None
        self.image_rel: Optional[str] = None

        form = ttk.Frame(self)
        form.pack(fill="both", expand=True, padx=10, pady=10)
        form.columnconfigure(1, weight=1)

        def add_row(r, label, var=None, width=35):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=3, padx=5)
            if var is None:
                ent = ttk.Entry(form, width=width)
            else:
                ent = ttk.Entry(form, textvariable=var, width=width)
            ent.grid(row=r, column=1, sticky="ew", pady=3, padx=5)
            return ent

        self.var_article = tk.StringVar()
        self.var_name = tk.StringVar()
        self.var_unit = tk.StringVar()
        self.var_cost = tk.StringVar()
        self.var_max_disc = tk.StringVar()
        self.var_manufacturer = tk.StringVar()
        self.var_supplier = tk.StringVar()
        self.var_category = tk.StringVar()
        self.var_discount = tk.StringVar()
        self.var_qty = tk.StringVar()

        add_row(0, "Артикул (при редактировании только чтение):", self.var_article)
        add_row(1, "Наименование:", self.var_name)
        add_row(2, "Ед. измерения:", self.var_unit)
        add_row(3, "Стоимость:", self.var_cost)
        add_row(4, "Макс. скидка (%):", self.var_max_disc)
        add_row(5, "Производитель:", self.var_manufacturer)
        add_row(6, "Поставщик:", self.var_supplier)
        add_row(7, "Категория:", self.var_category)
        add_row(8, "Действующая скидка (%):", self.var_discount)
        add_row(9, "Кол-во на складе:", self.var_qty)

        ttk.Label(form, text="Описание:").grid(row=10, column=0, sticky="nw", pady=3, padx=5)
        self.txt_desc = tk.Text(form, height=5)
        self.txt_desc.grid(row=10, column=1, sticky="nsew", pady=3, padx=5)

        img_row = ttk.Frame(form)
        img_row.grid(row=11, column=1, sticky="w", pady=(8, 0), padx=5)
        self.lbl_img = ttk.Label(img_row, text="Изображение: (не выбрано)")
        self.lbl_img.pack(side="left")
        ttk.Button(img_row, text="Выбрать...", command=self.pick_image).pack(side="left", padx=8)

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(btns, text="Удалить", command=self.delete).pack(side="left", padx=8)
        ttk.Button(btns, text="Назад", command=lambda: self.app.show(ProductListPage)).pack(side="right")

    def on_show(self) -> None:
        self.top.refresh_user()

    def set_product(self, article: Optional[str]) -> None:
        self.article = article
        self.image_rel = None
        self.txt_desc.delete("1.0", "end")
        self.lbl_img.config(text="Изображение: (не выбрано)")

        if article is None:
            self.top.lbl_title.config(text="Товар — добавление")
            self.var_article.set("")
            self.var_article_entry_state(False)
            self.delete_button_state(False)
            return

        self.top.lbl_title.config(text="Товар — редактирование")
        with get_conn() as conn:
            row = conn.execute("SELECT * FROM product WHERE article=?", (article,)).fetchone()
        if not row:
            messagebox.showerror("Ошибка", "Товар не найден в базе.")
            self.app.show(ProductListPage)
            return

        self.var_article.set(row["article"])
        self.var_name.set(row["name"])
        self.var_unit.set(row["unit"])
        self.var_cost.set(str(row["cost"]))
        self.var_max_disc.set(str(row["max_discount"]))
        self.var_manufacturer.set(row["manufacturer"])
        self.var_supplier.set(row["supplier"])
        self.var_category.set(row["category"])
        self.var_discount.set(str(row["discount"]))
        self.var_qty.set(str(row["quantity"]))
        self.txt_desc.insert("1.0", row["description"])
        self.image_rel = row["image_path"]
        if self.image_rel:
            self.lbl_img.config(text=f"Изображение: {self.image_rel}")
        self.var_article_entry_state(True)
        self.delete_button_state(True)

    def var_article_entry_state(self, readonly: bool) -> None:
        # Hack: find the entry bound to var_article (first child after label)
        # Simpler: traverse children and match variable name isn't exposed, so keep it basic:
        pass

    def delete_button_state(self, enabled: bool) -> None:
        # 2nd button in btn frame isn't directly stored; no big deal - allow delete only when editing
        # We'll enforce in delete().
        return

    def pick_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Выберите изображение (jpg/png)",
            filetypes=[("Images", "*.jpg *.jpeg *.png"), ("All files", "*.*")],
        )
        if not path:
            return
        src = Path(path)
        dst = ASSETS_PRODUCTS_DIR / src.name
        try:
            dst.write_bytes(src.read_bytes())
            rel = os.path.relpath(dst, APP_ROOT)
            self.image_rel = rel
            self.lbl_img.config(text=f"Изображение: {rel}")
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось сохранить изображение: {e}")

    def _validate(self) -> Optional[str]:
        if not self.var_name.get().strip():
            return "Не заполнено поле «Наименование»."
        try:
            cost = float(self.var_cost.get().strip())
            if cost < 0:
                return "Стоимость не может быть отрицательной."
        except Exception:
            return "Некорректная стоимость."
        try:
            qty = int(self.var_qty.get().strip())
            if qty < 0:
                return "Количество не может быть отрицательным."
        except Exception:
            return "Некорректное количество."
        for fld, label in [(self.var_discount, "Действующая скидка"), (self.var_max_disc, "Макс. скидка")]:
            try:
                v = int(fld.get().strip())
                if v < 0 or v > 100:
                    return f"Поле «{label}» должно быть в диапазоне 0..100."
            except Exception:
                return f"Некорректное значение в поле «{label}»."
        return None

    def save(self) -> None:
        err = self._validate()
        if err:
            messagebox.showerror("Ошибка ввода", err)
            return

        name = self.var_name.get().strip()
        unit = self.var_unit.get().strip() or "шт."
        cost = float(self.var_cost.get().strip())
        max_disc = int(self.var_max_disc.get().strip() or "0")
        manufacturer = self.var_manufacturer.get().strip()
        supplier = self.var_supplier.get().strip()
        category = self.var_category.get().strip()
        discount = int(self.var_discount.get().strip() or "0")
        qty = int(self.var_qty.get().strip())
        desc = self.txt_desc.get("1.0", "end").strip()

        with get_conn() as conn:
            if self.article is None:
                article = self.var_article.get().strip()
                if not article:
                    messagebox.showerror("Ошибка ввода", "Артикул обязателен при добавлении товара.")
                    return
                # ensure unique
                exists = conn.execute("SELECT 1 FROM product WHERE article=?", (article,)).fetchone()
                if exists:
                    messagebox.showerror("Ошибка", "Товар с таким артикулом уже существует.")
                    return
                conn.execute(
                    """
                    INSERT INTO product(article, name, unit, cost, max_discount, manufacturer, supplier, category,
                                        discount, quantity, description, image_path)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (article, name, unit, cost, max_disc, manufacturer, supplier, category, discount, qty, desc, self.image_rel),
                )
                self.article = article
            else:
                conn.execute(
                    """
                    UPDATE product
                    SET name=?, unit=?, cost=?, max_discount=?, manufacturer=?, supplier=?, category=?, discount=?, quantity=?,
                        description=?, image_path=?
                    WHERE article=?
                    """,
                    (name, unit, cost, max_disc, manufacturer, supplier, category, discount, qty, desc, self.image_rel, self.article),
                )

        messagebox.showinfo("Сохранено", "Данные товара сохранены.")
        self.app.show(ProductListPage)

    def delete(self) -> None:
        if self.article is None:
            return
        if not messagebox.askyesno("Подтверждение", "Удалить товар?"):
            return
        with get_conn() as conn:
            # cannot delete if used in orders
            used = conn.execute("SELECT 1 FROM order_product WHERE product_article=? LIMIT 1", (self.article,)).fetchone()
            if used:
                messagebox.showwarning("Удаление запрещено", "Товар присутствует в заказе — удалить нельзя.")
                return

            # remove image file if exists
            row = conn.execute("SELECT image_path FROM product WHERE article=?", (self.article,)).fetchone()
            if row and row["image_path"]:
                try:
                    img_path = (APP_ROOT / row["image_path"]).resolve()
                    if img_path.exists():
                        img_path.unlink()
                except Exception:
                    pass

            conn.execute("DELETE FROM product WHERE article=?", (self.article,))
        messagebox.showinfo("Удалено", "Товар удалён.")
        self.app.show(ProductListPage)


class OrdersPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: App):
        super().__init__(parent)
        self.app = app

        self.top = TopBar(self, app, "Заказы")
        self.top.pack(fill="x")

        controls = ttk.Frame(self)
        controls.pack(fill="x", padx=10, pady=5)

        self.btn_add = ttk.Button(controls, text="Добавить заказ", command=self.add_order)
        self.btn_add.pack(side="left")

        ttk.Button(controls, text="Назад к товарам", command=lambda: self.app.show(ProductListPage)).pack(side="right")

        self.tree = ttk.Treeview(
            self,
            columns=("id", "status", "order_date", "delivery_date", "pickup", "client", "code"),
            show="headings",
            height=20,
        )
        for col, title, w in [
            ("id", "№", 60),
            ("status", "Статус", 120),
            ("order_date", "Дата заказа", 110),
            ("delivery_date", "Дата выдачи", 110),
            ("pickup", "Пункт выдачи", 260),
            ("client", "Клиент", 200),
            ("code", "Код", 80),
        ]:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree.bind("<Double-1>", self.open_for_edit)

    def on_show(self) -> None:
        self.top.refresh_user()
        role = self.app.current_user.role if self.app.current_user else "Гость"
        if role == "Администратор":
            self.btn_add.state(["!disabled"])
        else:
            self.btn_add.state(["disabled"])
        self.refresh()

    def refresh(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        with get_conn() as conn:
            rows = conn.execute(
                """
                SELECT o.id, o.status, o.order_date, o.delivery_date, p.address AS pickup, o.client_name, o.pickup_code
                FROM "order" o
                JOIN pickup_point p ON p.id = o.pickup_point_id
                ORDER BY o.id
                """
            ).fetchall()
        for r in rows:
            self.tree.insert("", "end", iid=str(r["id"]), values=(r["id"], r["status"], r["order_date"], r["delivery_date"], r["pickup"], r["client_name"] or "", r["pickup_code"]))

    def _require_admin(self) -> bool:
        role = self.app.current_user.role if self.app.current_user else "Гость"
        if role != "Администратор":
            messagebox.showwarning("Доступ запрещён", "Действие доступно только Администратору.")
            return False
        return True

    def add_order(self) -> None:
        if not self._require_admin():
            return
        edit_page: OrderEditPage = self.app.frames[OrderEditPage]  # type: ignore[assignment]
        edit_page.set_order(order_id=None)
        self.app.show(OrderEditPage)

    def open_for_edit(self, _evt=None) -> None:
        if not self._require_admin():
            return
        sel = self.tree.selection()
        if not sel:
            return
        order_id = int(sel[0])
        edit_page: OrderEditPage = self.app.frames[OrderEditPage]  # type: ignore[assignment]
        edit_page.set_order(order_id=order_id)
        self.app.show(OrderEditPage)


class OrderEditPage(ttk.Frame):
    def __init__(self, parent: ttk.Frame, app: App):
        super().__init__(parent)
        self.app = app
        self.top = TopBar(self, app, "Заказ — добавление/редактирование")
        self.top.pack(fill="x")

        self.order_id: Optional[int] = None

        form = ttk.Frame(self)
        form.pack(fill="both", expand=True, padx=10, pady=10)
        form.columnconfigure(1, weight=1)

        self.var_id = tk.StringVar()
        self.var_status = tk.StringVar()
        self.var_order_date = tk.StringVar()
        self.var_delivery_date = tk.StringVar()
        self.var_pickup = tk.StringVar()
        self.var_client = tk.StringVar()
        self.var_code = tk.StringVar()
        self.var_items = tk.StringVar()

        def row(r, label, widget):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", padx=5, pady=3)
            widget.grid(row=r, column=1, sticky="ew", padx=5, pady=3)

        row(0, "Номер заказа:", ttk.Entry(form, textvariable=self.var_id))
        row(1, "Статус:", ttk.Entry(form, textvariable=self.var_status))
        row(2, "Дата заказа (YYYY-MM-DD):", ttk.Entry(form, textvariable=self.var_order_date))
        row(3, "Дата выдачи (YYYY-MM-DD):", ttk.Entry(form, textvariable=self.var_delivery_date))

        self.cmb_pickup = ttk.Combobox(form, textvariable=self.var_pickup, state="readonly")
        row(4, "Пункт выдачи:", self.cmb_pickup)

        row(5, "ФИО клиента:", ttk.Entry(form, textvariable=self.var_client))
        row(6, "Код для получения:", ttk.Entry(form, textvariable=self.var_code))
        row(7, "Состав заказа (формат: ART, QTY, ART, QTY):", ttk.Entry(form, textvariable=self.var_items))

        btns = ttk.Frame(self)
        btns.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btns, text="Сохранить", command=self.save).pack(side="left")
        ttk.Button(btns, text="Удалить", command=self.delete).pack(side="left", padx=8)
        ttk.Button(btns, text="Назад", command=lambda: self.app.show(OrdersPage)).pack(side="right")

    def on_show(self) -> None:
        self.top.refresh_user()

    def set_order(self, order_id: Optional[int]) -> None:
        self.order_id = order_id

        with get_conn() as conn:
            points = conn.execute("SELECT id, address FROM pickup_point ORDER BY id").fetchall()
        pickup_values = [f"{p['id']}: {p['address']}" for p in points]
        self.cmb_pickup["values"] = pickup_values

        # reset
        for v in (self.var_id, self.var_status, self.var_order_date, self.var_delivery_date, self.var_pickup, self.var_client, self.var_code, self.var_items):
            v.set("")

        if order_id is None:
            self.top.lbl_title.config(text="Заказ — добавление")
            return

        self.top.lbl_title.config(text="Заказ — редактирование")
        with get_conn() as conn:
            row = conn.execute('SELECT * FROM "order" WHERE id=?', (order_id,)).fetchone()
            items = conn.execute('SELECT product_article, quantity FROM order_product WHERE order_id=?', (order_id,)).fetchall()
            pickup = conn.execute("SELECT id, address FROM pickup_point WHERE id=?", (row["pickup_point_id"],)).fetchone()

        self.var_id.set(str(row["id"]))
        self.var_status.set(row["status"])
        self.var_order_date.set(row["order_date"])
        self.var_delivery_date.set(row["delivery_date"])
        self.var_pickup.set(f"{pickup['id']}: {pickup['address']}")
        self.var_client.set(row["client_name"] or "")
        self.var_code.set(str(row["pickup_code"]))
        flat = []
        for it in items:
            flat += [it["product_article"], str(it["quantity"])]
        self.var_items.set(", ".join(flat))

    def _parse_pickup_id(self) -> Optional[int]:
        txt = self.var_pickup.get().strip()
        if not txt:
            return None
        try:
            return int(txt.split(":", 1)[0])
        except Exception:
            return None

    def _parse_items(self) -> list[tuple[str, int]]:
        parts = [p.strip() for p in self.var_items.get().split(",") if p.strip()]
        items = []
        for i in range(0, len(parts) - 1, 2):
            art = parts[i]
            try:
                qty = int(parts[i + 1])
            except Exception:
                continue
            if qty > 0:
                items.append((art, qty))
        return items

    def _validate(self) -> Optional[str]:
        try:
            _ = int(self.var_id.get().strip())
        except Exception:
            return "Номер заказа должен быть целым числом."
        if not self.var_status.get().strip():
            return "Не заполнен статус."
        for fld, label in [(self.var_order_date, "Дата заказа"), (self.var_delivery_date, "Дата выдачи")]:
            try:
                # basic ISO
                parts = fld.get().strip().split("-")
                if len(parts) != 3:
                    raise ValueError
                y, m, d = map(int, parts)
                _ = (y, m, d)
            except Exception:
                return f"Некорректное значение в поле «{label}». Используйте YYYY-MM-DD."
        if not self._parse_pickup_id():
            return "Не выбран пункт выдачи."
        try:
            _ = int(self.var_code.get().strip())
        except Exception:
            return "Код получения должен быть целым числом."
        # Items optional
        return None

    def save(self) -> None:
        err = self._validate()
        if err:
            messagebox.showerror("Ошибка ввода", err)
            return

        order_id = int(self.var_id.get().strip())
        status = self.var_status.get().strip()
        order_date = self.var_order_date.get().strip()
        delivery_date = self.var_delivery_date.get().strip()
        pickup_id = self._parse_pickup_id()
        client = self.var_client.get().strip() or None
        code = int(self.var_code.get().strip())
        items = self._parse_items()

        with get_conn() as conn:
            exists = conn.execute('SELECT 1 FROM "order" WHERE id=?', (order_id,)).fetchone()
            if self.order_id is None and exists:
                messagebox.showerror("Ошибка", "Заказ с таким номером уже существует.")
                return

            if exists:
                conn.execute(
                    """
                    UPDATE "order"
                    SET status=?, order_date=?, delivery_date=?, pickup_point_id=?, client_name=?, pickup_code=?
                    WHERE id=?
                    """,
                    (status, order_date, delivery_date, pickup_id, client, code, order_id),
                )
                conn.execute("DELETE FROM order_product WHERE order_id=?", (order_id,))
            else:
                conn.execute(
                    """
                    INSERT INTO "order"(id, status, order_date, delivery_date, pickup_point_id, client_name, pickup_code)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (order_id, status, order_date, delivery_date, pickup_id, client, code),
                )

            for art, qty in items:
                prod = conn.execute("SELECT 1 FROM product WHERE article=?", (art,)).fetchone()
                if not prod:
                    messagebox.showwarning("Предупреждение", f"Товар {art} не найден — пропущен в составе заказа.")
                    continue
                conn.execute("INSERT INTO order_product(order_id, product_article, quantity) VALUES (?, ?, ?)", (order_id, art, qty))

        messagebox.showinfo("Сохранено", "Данные заказа сохранены.")
        self.app.show(OrdersPage)

    def delete(self) -> None:
        if self.order_id is None:
            return
        if not messagebox.askyesno("Подтверждение", "Удалить заказ?"):
            return
        with get_conn() as conn:
            conn.execute('DELETE FROM "order" WHERE id=?', (self.order_id,))
        messagebox.showinfo("Удалено", "Заказ удалён.")
        self.app.show(OrdersPage)


def main() -> None:
    init_db_if_needed()
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
