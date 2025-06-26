import base64
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
import os
import datetime

def generate_report(df, insights):
    # Load chart image and encode as base64
    chart_path = "static/spend_chart.png"
    with open(chart_path, "rb") as image_file:
        chart_base64 = base64.b64encode(image_file.read()).decode("utf-8")

    # Setup Jinja2
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("report_template.html")

    # Render HTML
    html = template.render(
        campaigns=df.to_dict(orient="records"),
        insights=insights.replace('\n', '<br>'),
        chart_base64=chart_base64,
        now=datetime.date.today().strftime("%Y-%m-%d")
    )

    # Save output
    os.makedirs("reports", exist_ok=True)
    pdf_path = "reports/daily_kpi_report.pdf"
    html_path = "reports/daily_kpi_report_email.html"

    HTML(string=html).write_pdf(pdf_path)

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    return pdf_path