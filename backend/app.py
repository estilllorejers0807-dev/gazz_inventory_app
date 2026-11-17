import sys
import os
import io


from flask import (
    Flask,
    redirect,
    url_for,
    send_file,
    request,
    jsonify
)


from flask_login import (
    LoginManager,
    login_required,
    current_user,
    UserMixin
)


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


# =========================================================
# PATH CONFIGURATION
# =========================================================

current_dir = os.path.dirname(
    os.path.abspath(__file__)
)


parent_dir = os.path.dirname(
    current_dir
)


sys.path.insert(
    0,
    parent_dir
)


sys.path.insert(
    0,
    current_dir
)


# =========================================================
# IMPORTS
# =========================================================

from config import Config


from database.connection import (
    init_db,
    mysql
)


from routes.auth import auth_bp
from routes.products import products_bp
from routes.fuel import fuel_bp
from routes.sales import sales_bp
from routes.reports import reports_bp
from routes.admin import admin_bp
from routes.users import users_bp
from routes.api_auth import api_auth_bp
from routes.api_products import api_products_bp
from routes.api_fuel import api_fuel_bp
from routes.api_sales import api_sales_bp
from routes.api_reports import api_reports_bp
from routes.api_admin import api_admin_bp
from routes.api_users import api_users_bp


# =========================================================
# FRONTEND PATH
# =========================================================

base_dir = (

    parent_dir

    if os.path.exists(

        os.path.join(
            parent_dir,
            "frontend"
        )

    )

    else current_dir

)


template_folder = os.path.join(

    base_dir,
    "frontend",
    "templates"

)


static_folder = os.path.join(

    base_dir,
    "frontend"

)


# =========================================================
# FLASK APP
# =========================================================

app = Flask(

    __name__,

    template_folder=template_folder,

    static_folder=static_folder,

    static_url_path=""

)


app.config.from_object(
    Config
)


# =========================================================
# DATABASE
# =========================================================

init_db(
    app
)


# =========================================================
# USER MODEL FOR FLASK-LOGIN
# =========================================================

class User(UserMixin):


    def __init__(
        self,
        user_id,
        username,
        role,
        full_name=""
    ):


        self.id = user_id

        self.username = username

        self.role = role

        self.full_name = full_name


# =========================================================
# LOGIN MANAGER
# =========================================================

login_manager = LoginManager()


login_manager.init_app(
    app
)


login_manager.login_view = (
    "auth.login"
)


# =========================================================
# LOAD USER
# =========================================================

@login_manager.user_loader
def load_user(user_id):


    cursor = None


    try:


        cursor = mysql.connection.cursor()


        cursor.execute(

            """

            SELECT

                user_id,

                username,

                role,

                full_name


            FROM users


            WHERE

                user_id = %s

                AND is_active = 1

            """,

            (
                user_id,
            )

        )


        user_data = cursor.fetchone()


        if user_data:


            # Supports DictCursor
            if isinstance(
                user_data,
                dict
            ):


                return User(

                    user_data["user_id"],

                    user_data["username"],

                    user_data["role"],

                    user_data.get(
                        "full_name",
                        ""
                    )

                )


            # Supports normal tuple cursor
            return User(

                user_data[0],

                user_data[1],

                user_data[2],

                user_data[3]
                if len(user_data) > 3
                else ""

            )


    except Exception as error:


        print(
            "User loader error:",
            error
        )


    finally:


        if cursor:

            cursor.close()


    return None


# =========================================================
# REGISTER BLUEPRINTS
# =========================================================

app.register_blueprint(

    auth_bp,

    url_prefix="/auth"

)

# =========================================================
# API BLUEPRINTS
# =========================================================

# =========================================================
# API BLUEPRINTS
# =========================================================

app.register_blueprint(
    api_auth_bp,
    url_prefix="/api/auth"
)

app.register_blueprint(
    api_products_bp,
    url_prefix="/api/products"
)

app.register_blueprint(
    api_fuel_bp,
    url_prefix="/api/fuel"
)

app.register_blueprint(
    api_sales_bp,
    url_prefix="/api/sales"
)

app.register_blueprint(
    api_reports_bp,
    url_prefix="/api/reports"
)

app.register_blueprint(
    api_admin_bp,
    url_prefix="/api/admin"
)

app.register_blueprint(
    api_users_bp,
    url_prefix="/api/users"
)


app.register_blueprint(

    products_bp

)


app.register_blueprint(

    fuel_bp

)


app.register_blueprint(

    sales_bp

)


app.register_blueprint(

    reports_bp

)

app.register_blueprint(admin_bp)

app.register_blueprint(users_bp)


# =========================================================
# LOW STOCK NOTIFICATIONS
# =========================================================

@app.context_processor
def inject_notifications():


    if not current_user.is_authenticated:


        return dict(

            low_stock_alerts=[]

        )


    cursor = None


    try:


        cursor = mysql.connection.cursor()


        cursor.execute(

            """

            SELECT

                p.product_id,

                p.product_name,

                'Store' AS category_name,

                i.stock_quantity,

                p.low_stock_threshold


            FROM inventory i


            JOIN products p

                ON i.product_id = p.product_id

            WHERE

                i.stock_quantity
                    <= p.low_stock_threshold

                AND p.is_active = 1


            ORDER BY

                i.stock_quantity ASC

            """

        )


        alerts = cursor.fetchall()


        return dict(

            low_stock_alerts=alerts

        )


    except Exception as error:


        print(

            "Notification error:",
            error

        )


        return dict(

            low_stock_alerts=[]

        )


    finally:


        if cursor:

            cursor.close()


# =========================================================
# PDF EXPORT
# =========================================================

@app.route("/export-pdf/<report_type>")
@login_required
def export_pdf(report_type):

    if current_user.role not in ("manager", "admin"):
        return "Unauthorized Access", 403

    if report_type not in ("store", "fuel"):
        return "Invalid report type", 404

    start_date = request.args.get("start_date", "2026-01-01")
    end_date = request.args.get("end_date", "2026-12-31")

    cursor = None

    try:
        cursor = mysql.connection.cursor()

        if report_type == "store":
            cursor.execute("""
                SELECT
                    p.product_name,
                    'Store' AS category_name,
                    COALESCE(SUM(si.quantity), 0) AS qty,
                    COALESCE(SUM(si.subtotal), 0) AS revenue,
                    COALESCE(
                        SUM(
                            (si.unit_price - p.cost_price)
                            * si.quantity
                        ), 0
                    ) AS profit
                FROM sale_items si
                INNER JOIN sales s
                    ON si.sale_id = s.sale_id
                INNER JOIN products p
                    ON si.product_id = p.product_id
                WHERE
                    DATE(s.sale_date) BETWEEN %s AND %s
                    AND s.status = 'completed'
                    AND s.sale_type = 'store'
                GROUP BY
                    p.product_id,
                    p.product_name,
                    p.cost_price
                ORDER BY qty DESC
            """, (start_date, end_date))

            rows = cursor.fetchall()

            title = "GAZZ POS - Store Sales & Profit Report"
            filename = "GAZZ_Store_Report.pdf"
            headers = ["Product", "Category", "Qty Sold", "Revenue", "Profit"]

        else:
            cursor.execute("""
                SELECT
                    ft.fuel_name,
                    COALESCE(SUM(fs.liters), 0) AS liters_sold,
                    COALESCE(SUM(fs.total_amount), 0) AS revenue,
                    COALESCE(
                        SUM(
                            (fs.price_per_liter - ft.cost_per_liter)
                            * fs.liters
                        ), 0
                    ) AS profit
                FROM fuel_sales fs
                INNER JOIN sales s
                    ON fs.sale_id = s.sale_id
                INNER JOIN fuel_types ft
                    ON fs.fuel_type_id = ft.fuel_type_id
                WHERE
                    DATE(s.sale_date) BETWEEN %s AND %s
                    AND s.status = 'completed'
                    AND s.sale_type = 'fuel'
                GROUP BY
                    ft.fuel_type_id,
                    ft.fuel_name,
                    ft.cost_per_liter
                ORDER BY liters_sold DESC
            """, (start_date, end_date))

            rows = cursor.fetchall()

            title = "GAZZ POS - Fuel Sales & Profit Report"
            filename = "GAZZ_Fuel_Report.pdf"
            headers = ["Fuel Type", "Liters Sold", "Revenue", "Profit"]

    except Exception as error:
        print(f"PDF REPORT ERROR ({report_type}): {error}")
        raise

    finally:
        if cursor:
            cursor.close()

    # CREATE PDF
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)

    pdf.setTitle(title)

    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, 750, title)

    pdf.setFont("Helvetica", 10)
    pdf.drawString(
        40, 735,
        f"Date Range: {start_date} to {end_date}"
    )

    y = 690

    def draw_headers():
        pdf.setFont("Helvetica-Bold", 10)

        if report_type == "store":
            positions = [40, 200, 300, 380, 480]
        else:
            positions = [40, 230, 350, 470]

        for position, header in zip(positions, headers):
            pdf.drawString(position, y, header)

        pdf.line(40, y - 5, 550, y - 5)

    draw_headers()

    y -= 25
    pdf.setFont("Helvetica", 10)

    for row in rows:

        if isinstance(row, dict):
            if report_type == "store":
                values = [
                    row["product_name"],
                    row["category_name"],
                    row["qty"],
                    row["revenue"],
                    row["profit"]
                ]
            else:
                values = [
                    row["fuel_name"],
                    row["liters_sold"],
                    row["revenue"],
                    row["profit"]
                ]
        else:
            values = list(row)

        if report_type == "store":
            positions = [40, 200, 300, 380, 480]
            values = [
                str(values[0])[:22],
                str(values[1])[:15],
                str(values[2]),
                f"P{float(values[3] or 0):,.2f}",
                f"P{float(values[4] or 0):,.2f}"
            ]
        else:
            positions = [40, 230, 350, 470]
            values = [
                str(values[0])[:28],
                f"{float(values[1] or 0):,.3f} L",
                f"P{float(values[2] or 0):,.2f}",
                f"P{float(values[3] or 0):,.2f}"
            ]

        for position, value in zip(positions, values):
            pdf.drawString(position, y, str(value))

        y -= 20

        if y < 50:
            pdf.showPage()
            y = 750
            draw_headers()
            y -= 25
            pdf.setFont("Helvetica", 10)

    pdf.save()
    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype="application/pdf"
    )


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():


    return redirect(

        url_for(

            "auth.login"

        )

    )


# =========================================================
# RUN APPLICATION
# =========================================================

if __name__ == "__main__":


    app.run(

        debug=True

    )
