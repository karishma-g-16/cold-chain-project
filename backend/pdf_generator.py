"""
PDF REPORT GENERATOR
====================
Cold Chain Compliance Report generate karta hai.
InfluxDB se data fetch karke PDF mein format karta hai.
"""

import os
import sys
from datetime import datetime
from typing import Optional
from dotenv import load_dotenv

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    HRFlowable,
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# Import fix
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from backend.database import InfluxDBHandler

# Load env
env_path = os.path.join(parent_dir, "config", ".env")
load_dotenv(env_path)


class ColdChainPDFReport:
    """Cold Chain Compliance PDF Report Generator"""

    def __init__(self):
        self.db = InfluxDBHandler()
        self.temp_min = float(os.getenv("TEMP_MIN", 2.0))
        self.temp_max = float(os.getenv("TEMP_MAX", 8.0))

        # Colors
        self.primary_color = colors.HexColor("#1a73e8")
        self.danger_color = colors.HexColor("#d93025")
        self.success_color = colors.HexColor("#1e8e3e")
        self.warning_color = colors.HexColor("#f9ab00")
        self.light_gray = colors.HexColor("#f8f9fa")
        self.dark_gray = colors.HexColor("#3c4043")

    def generate(
        self,
        output_path: str = None,
        device_id: str = None,
        minutes: int = 1440,  # Last 24 hours
    ) -> str:
        """
        PDF report generate karo

        Args:
            output_path: PDF save karne ka path
            device_id: Specific device (None = all)
            minutes: Last N minutes ka data

        Returns:
            str: Generated PDF path
        """

        # Connect to InfluxDB
        if not self.db.connect():
            print("❌ InfluxDB connection failed")
            return None

        # Data fetch karo
        readings = self.db.get_recent_readings(device_id=device_id, minutes=minutes)
        self.db.disconnect()

        if not readings:
            print("⚠️  No data found for report")
            return None

        # Output path
        if not output_path:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            output_dir = os.path.join(parent_dir, "data")
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, f"coldchain_report_{timestamp}.pdf")

        # PDF generate karo
        doc = SimpleDocTemplate(
            output_path,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Content build karo
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "Title",
            parent=styles["Normal"],
            fontSize=22,
            fontName="Helvetica-Bold",
            textColor=self.primary_color,
            alignment=TA_CENTER,
            spaceAfter=16,
        )

        subtitle_style = ParagraphStyle(
            "Subtitle",
            parent=styles["Normal"],
            fontSize=11,
            fontName="Helvetica",
            textColor=self.dark_gray,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=8,
        )

        section_style = ParagraphStyle(
            "Section",
            parent=styles["Normal"],
            fontSize=13,
            fontName="Helvetica-Bold",
            textColor=self.primary_color,
            spaceBefore=12,
            spaceAfter=6,
        )

        normal_style = ParagraphStyle(
            "Normal2",
            parent=styles["Normal"],
            fontSize=10,
            fontName="Helvetica",
            textColor=self.dark_gray,
        )

        # ── HEADER ──
        story.append(Paragraph("Cold Chain Compliance Report", title_style))
        story.append(
            Paragraph("Automated Cold Chain Compliance Logger", subtitle_style)
        )
        story.append(
            Paragraph(
                f"Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
                subtitle_style,
            )
        )
        story.append(HRFlowable(width="100%", thickness=2, color=self.primary_color))
        story.append(Spacer(1, 12))

        # ── SUMMARY ──
        story.append(Paragraph("Report Summary", section_style))

        # Calculate stats
        violations = [
            r
            for r in readings
            if r.get("temperature") is not None
            and (r["temperature"] < self.temp_min or r["temperature"] > self.temp_max)
        ]
        compliant = len(readings) - len(violations)
        compliance_rate = round((compliant / len(readings)) * 100, 1) if readings else 0

        temps = [r["temperature"] for r in readings if r.get("temperature") is not None]
        avg_temp = round(sum(temps) / len(temps), 2) if temps else 0
        max_temp = round(max(temps), 2) if temps else 0
        min_temp = round(min(temps), 2) if temps else 0

        devices = list(set(r.get("device_id") for r in readings if r.get("device_id")))

        summary_data = [
            ["Metric", "Value"],
            ["Report Period", f"Last {minutes // 60} hours"],
            ["Total Readings", str(len(readings))],
            ["Active Devices", str(len(devices))],
            ["Violations", str(len(violations))],
            ["Compliance Rate", f"{compliance_rate}%"],
            ["Avg Temperature", f"{avg_temp}°C"],
            ["Max Temperature", f"{max_temp}°C"],
            ["Min Temperature", f"{min_temp}°C"],
            ["Safe Range", f"{self.temp_min}°C - {self.temp_max}°C"],
        ]

        summary_table = Table(summary_data, colWidths=[2.5 * inch, 3 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 1), (-1, -1), 10),
                    ("BACKGROUND", (0, 1), (-1, -1), self.light_gray),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, self.light_gray],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
                    ("LEFTPADDING", (0, 0), (-1, -1), 10),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    # Compliance rate color
                    (
                        "TEXTCOLOR",
                        (1, 5),
                        (1, 5),
                        (
                            self.success_color
                            if compliance_rate >= 90
                            else self.danger_color
                        ),
                    ),
                    ("FONTNAME", (1, 5), (1, 5), "Helvetica-Bold"),
                ]
            )
        )

        story.append(summary_table)
        story.append(Spacer(1, 16))

        # ── VIOLATIONS ──
        if violations:
            story.append(Paragraph(f"Violations ({len(violations)})", section_style))

            viol_data = [["Time", "Device", "Temperature", "Humidity", "Status"]]
            for v in violations[:20]:  # Max 20 violations
                temp = v.get("temperature", 0)
                time_str = str(v.get("time", ""))[:19].replace("T", " ")
                viol_data.append(
                    [
                        time_str,
                        v.get("device_id", "N/A"),
                        f"{temp}°C",
                        f"{v.get('humidity', 'N/A')}%",
                        "TOO HIGH" if temp > self.temp_max else "TOO LOW",
                    ]
                )

            viol_table = Table(
                viol_data,
                colWidths=[1.8 * inch, 1.2 * inch, 1.1 * inch, 1.0 * inch, 1.2 * inch],
            )
            viol_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), self.danger_color),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#fce8e6")],
                        ),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
                        ("TOPPADDING", (0, 0), (-1, -1), 5),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                        ("TEXTCOLOR", (4, 1), (4, -1), self.danger_color),
                        ("FONTNAME", (4, 1), (4, -1), "Helvetica-Bold"),
                    ]
                )
            )
            story.append(viol_table)
            story.append(Spacer(1, 16))

        # ── ALL READINGS ──
        story.append(Paragraph(f"All Readings ({len(readings)})", section_style))

        readings_data = [["Time", "Device", "Temp (°C)", "Humidity (%)", "Status"]]
        for r in readings[:50]:  # Max 50 readings
            temp = r.get("temperature", 0)
            status = "✓ OK" if self.temp_min <= temp <= self.temp_max else "✗ VIOLATION"
            time_str = str(r.get("time", ""))[:19].replace("T", " ")
            readings_data.append(
                [
                    time_str,
                    r.get("device_id", "N/A"),
                    f"{temp}",
                    f"{r.get('humidity', 'N/A')}",
                    status,
                ]
            )

        readings_table = Table(
            readings_data,
            colWidths=[1.8 * inch, 1.2 * inch, 1.1 * inch, 1.2 * inch, 1.0 * inch],
        )
        readings_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), self.primary_color),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, self.light_gray],
                    ),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dadce0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )

        # Violation rows red karo
        for i, r in enumerate(readings[:50], start=1):
            temp = r.get("temperature", 0)
            if temp < self.temp_min or temp > self.temp_max:
                readings_table.setStyle(
                    TableStyle(
                        [
                            ("TEXTCOLOR", (4, i), (4, i), self.danger_color),
                            ("FONTNAME", (4, i), (4, i), "Helvetica-Bold"),
                        ]
                    )
                )

        story.append(readings_table)
        story.append(Spacer(1, 16))

        # ── FOOTER ──
        story.append(
            HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dadce0"))
        )
        story.append(Spacer(1, 6))
        story.append(
            Paragraph(
                "Generated by Automated Cold Chain Compliance Logger | "
                "FastAPI + MQTT + InfluxDB + Telegram",
                ParagraphStyle(
                    "Footer",
                    parent=styles["Normal"],
                    fontSize=8,
                    textColor=colors.gray,
                    alignment=TA_CENTER,
                ),
            )
        )

        # PDF build karo
        doc.build(story)
        print(f"✅ PDF Report generated: {output_path}")
        return output_path


# Test code
if __name__ == "__main__":
    print("📄 Generating Cold Chain Compliance Report...")

    generator = ColdChainPDFReport()
    pdf_path = generator.generate(minutes=1440)

    if pdf_path:
        print(f"✅ Report saved at: {pdf_path}")
    else:
        print("❌ Failed to generate report")
