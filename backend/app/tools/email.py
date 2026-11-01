import asyncio
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from html import escape

from ..config import Settings, settings


def is_valid_email(email: str) -> bool:
    if not email:
        return False
    return bool(re.fullmatch(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email.strip()))


def generate_itinerary_text(trip_data: dict) -> str:
    plan = trip_data.get("plan") or {}
    req = trip_data.get("request") or {}
    sel = trip_data.get("selection") or {}
    flights = {f["id"]: f for f in trip_data.get("flights", [])}
    hotels = {h["id"]: h for h in trip_data.get("hotels", [])}

    flight = flights.get(sel.get("flight_id"))
    hotel = hotels.get(sel.get("hotel_id"))

    lines = []
    lines.append(f"=== {plan.get('title', 'Your Travel Itinerary')} ===")
    if plan.get("summary"):
        lines.append(f"\n{plan['summary']}\n")

    lines.append("TRIP DETAILS:")
    if req.get("destination"):
        lines.append(f"Destination: {req['destination']}")
    if req.get("start_date") and req.get("end_date"):
        lines.append(f"Dates: {req['start_date']} to {req['end_date']}")
    if req.get("travelers"):
        lines.append(f"Travelers: {req['travelers']}")

    if flight:
        stops = "Nonstop" if flight.get("stops") == 0 else f"{flight.get('stops')} stops"
        lines.append(f"\nFLIGHT: {flight.get('airline')} ({stops}) - {flight.get('price'):,.0f} {flight.get('currency')}")

    if hotel:
        lines.append(f"HOTEL: {hotel.get('name')} - {hotel.get('price_per_night'):,.0f} {hotel.get('currency')}/night")

    if sel:
        lines.append(f"\nESTIMATED TOTAL: {sel.get('total', 0):,.0f} {sel.get('currency', 'USD')}")
        lines.append(f"  Flights: {sel.get('flights_cost', 0):,.0f} {sel.get('currency')}")
        lines.append(f"  Stay: {sel.get('hotel_cost', 0):,.0f} {sel.get('currency')}")
        lines.append(f"  Daily expenses: {sel.get('daily_cost', 0):,.0f} {sel.get('currency')}")

    lines.append("\nDAY-BY-DAY ITINERARY:")
    for i, day in enumerate(plan.get("days", []), start=1):
        lines.append(f"\n--- Day {i}: {day.get('date')} ({day.get('theme', 'Exploration')}) ---")
        for item in day.get("items", []):
            tod = item.get("time_of_day", "").capitalize()
            place = f" @ {item['place']}" if item.get("place") else ""
            lines.append(f"  [{tod}] {item.get('title')}{place}")
            if item.get("description"):
                lines.append(f"    {item['description']}")

    tips = plan.get("tips", [])
    if tips:
        lines.append("\nPRACTICAL TRAVEL TIPS:")
        for tip in tips:
            lines.append(f"- {tip}")

    lines.append("\n---\nCreated with Wayfinder AI Travel Agent")
    return "\n".join(lines)


def generate_itinerary_html(trip_data: dict) -> str:
    plan = trip_data.get("plan") or {}
    req = trip_data.get("request") or {}
    sel = trip_data.get("selection") or {}
    flights = {f["id"]: f for f in trip_data.get("flights", [])}
    hotels = {h["id"]: h for h in trip_data.get("hotels", [])}

    flight = flights.get(sel.get("flight_id"))
    hotel = hotels.get(sel.get("hotel_id"))

    curr = sel.get("currency", req.get("currency", "USD"))
    title = escape(plan.get("title", f"Trip to {req.get('destination', 'Your Destination')}"))
    summary = escape(plan.get("summary", ""))

    days_html = ""
    for i, day in enumerate(plan.get("days", []), start=1):
        items_html = ""
        for item in day.get("items", []):
            tod = escape(item.get("time_of_day", "").capitalize())
            it_title = escape(item.get("title", ""))
            it_desc = escape(item.get("description", ""))
            place = f'<span style="color:#666;font-size:12px;"> · {escape(item["place"])}</span>' if item.get("place") else ""
            cost = f'<span style="float:right;font-weight:600;color:#0b7a62;">{item.get("est_cost"):,.0f} {curr}</span>' if item.get("est_cost") else ""
            items_html += f"""
            <div style="margin: 10px 0; padding: 12px; background: #fafafa; border-left: 3px solid #d6284a; border-radius: 4px;">
              <div style="font-size: 11px; text-transform: uppercase; font-weight: bold; color: #888;">{tod} {cost}</div>
              <div style="font-weight: 600; font-size: 15px; margin: 2px 0;">{it_title} {place}</div>
              <div style="color: #444; font-size: 13px; line-height: 1.4;">{it_desc}</div>
            </div>
            """
        day_date = escape(day.get("date", ""))
        day_theme = escape(day.get("theme", "Exploration"))
        days_html += f"""
        <div style="margin-bottom: 24px; padding: 16px; border: 1px solid #eee; border-radius: 8px;">
          <h3 style="margin: 0 0 12px; color: #111; font-size: 17px;">Day {i} · {day_date} <span style="font-size: 14px; font-weight: normal; color: #777;">({day_theme})</span></h3>
          {items_html}
        </div>
        """

    tips_html = ""
    if plan.get("tips"):
        tips_list = "".join(f"<li style='margin-bottom:6px;'>{escape(t)}</li>" for t in plan["tips"])
        tips_html = f"""
        <div style="background: #f7f9fa; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-top: 24px;">
          <h4 style="margin: 0 0 10px; font-size: 15px; color: #1a202c;">💡 Practical Travel Tips</h4>
          <ul style="margin: 0; padding-left: 20px; color: #4a5568; font-size: 14px; line-height: 1.5;">
            {tips_list}
          </ul>
        </div>
        """

    flight_html = ""
    if flight:
        stops_text = "Nonstop" if flight.get("stops") == 0 else f"{flight.get('stops')} stops"
        flight_html = f"""
        <div style="background: #fdf2f4; border: 1px solid #fed7df; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
          <div style="font-size: 12px; font-weight: bold; color: #d6284a;">✈️ SELECTED FLIGHT</div>
          <div style="font-size: 16px; font-weight: bold; color: #111; margin-top: 2px;">{escape(flight.get('airline', 'Flight'))}</div>
          <div style="font-size: 13px; color: #555;">{stops_text} · {flight.get('price', 0):,.0f} {escape(flight.get('currency', curr))} per traveler</div>
        </div>
        """

    hotel_html = ""
    if hotel:
        rating_text = f"★ {hotel.get('rating', '')}" if hotel.get("rating") else ""
        hotel_html = f"""
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 14px; margin-bottom: 12px;">
          <div style="font-size: 12px; font-weight: bold; color: #15803d;">🏨 SELECTED STAY</div>
          <div style="font-size: 16px; font-weight: bold; color: #111; margin-top: 2px;">{escape(hotel.get('name', 'Hotel'))} <span style="font-size:13px;color:#15803d;">{rating_text}</span></div>
          <div style="font-size: 13px; color: #555;">{hotel.get('price_per_night', 0):,.0f} {escape(hotel.get('currency', curr))} / night</div>
        </div>
        """

    cost_html = ""
    if sel:
        cost_html = f"""
        <div style="background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; margin-bottom: 24px;">
          <div style="font-size: 13px; color: #718096; text-transform: uppercase; font-weight: 600;">Estimated Trip Cost</div>
          <div style="font-size: 26px; font-weight: 800; color: #1a202c; margin: 4px 0 12px;">{sel.get('total', 0):,.0f} {curr}</div>
          <div style="display: flex; gap: 16px; font-size: 13px; color: #4a5568;">
            <span>Flights: <strong>{sel.get('flights_cost', 0):,.0f} {curr}</strong></span>
            <span>Stay: <strong>{sel.get('hotel_cost', 0):,.0f} {curr}</strong></span>
            <span>Food & Activities: <strong>{sel.get('daily_cost', 0):,.0f} {curr}</strong></span>
          </div>
        </div>
        """

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>{title}</title>
      </head>
      <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b;">
        <div style="max-width: 640px; margin: 0 auto; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 32px; box-shadow: 0 2px 8px rgba(0,0,0,0.04);">
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 20px;">
            <span style="font-size: 20px; font-weight: bold; color: #d6284a;">✈️ Wayfinder</span>
            <span style="font-size: 12px; background: #f1f5f9; padding: 2px 8px; border-radius: 12px; color: #64748b; font-weight: 600;">AI Travel Plan</span>
          </div>
          <h1 style="font-size: 24px; font-weight: 800; margin: 0 0 10px; color: #0f172a;">{title}</h1>
          <p style="font-size: 15px; line-height: 1.5; color: #475569; margin: 0 0 20px;">{summary}</p>

          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 20px;">
            {flight_html}
            {hotel_html}
          </div>

          {cost_html}

          <h2 style="font-size: 18px; font-weight: 700; margin: 28px 0 16px; color: #0f172a; border-bottom: 2px solid #f1f5f9; padding-bottom: 8px;">Itinerary Schedule</h2>
          {days_html}

          {tips_html}

          <div style="margin-top: 36px; padding-top: 16px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">
            Sent by Wayfinder AI Travel Agent · Have a wonderful and safe journey!
          </div>
        </div>
      </body>
    </html>
    """


async def send_itinerary_email(to_email: str, trip_data: dict) -> dict:
    """Sends the itinerary to to_email via SMTP if configured, or simulates delivery in demo mode."""
    to_email = to_email.strip()
    if not is_valid_email(to_email):
        return {"ok": False, "status": "error", "message": f"'{to_email}' is not a valid email address."}

    plan = trip_data.get("plan") or {}
    title = plan.get("title", "Your Travel Itinerary")
    subject = f"✈️ Your Itinerary: {title}"

    text_body = generate_itinerary_text(trip_data)
    html_body = generate_itinerary_html(trip_data)

    cfg = Settings()

    if cfg.smtp_host:
        def _send():
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = cfg.smtp_from or cfg.smtp_user or "wayfinder@travel-agent.ai"
            msg["To"] = to_email
            msg.attach(MIMEText(text_body, "plain", "utf-8"))
            msg.attach(MIMEText(html_body, "html", "utf-8"))

            server = None
            try:
                if cfg.smtp_port == 465:
                    server = smtplib.SMTP_SSL(cfg.smtp_host, cfg.smtp_port, timeout=cfg.http_timeout)
                else:
                    server = smtplib.SMTP(cfg.smtp_host, cfg.smtp_port, timeout=cfg.http_timeout)
                    server.ehlo()
                    server.starttls()
                    server.ehlo()

                if cfg.smtp_user and cfg.smtp_password:
                    clean_pw = cfg.smtp_password.replace(" ", "")
                    server.login(cfg.smtp_user, clean_pw)

                sender = cfg.smtp_from or cfg.smtp_user
                server.sendmail(sender, [to_email], msg.as_string())
            except smtplib.SMTPAuthenticationError as e:
                raise RuntimeError(
                    f"Authentication failed for {cfg.smtp_user}. "
                    "For Gmail, you must generate a 16-character App Password "
                    "(Google Account -> Security -> 2-Step Verification -> App passwords). "
                    "Your regular Gmail account password will not work."
                ) from e
            except smtplib.SMTPServerDisconnected as e:
                raise RuntimeError(
                    f"Gmail/SMTP server disconnected during authentication for {cfg.smtp_user}. "
                    "Ensure 2-Step Verification is enabled and that you are using a 16-character App Password."
                ) from e
            finally:
                if server is not None:
                    try:
                        server.close()
                    except Exception:
                        pass

        try:
            await asyncio.to_thread(_send)
            return {
                "ok": True,
                "status": "sent",
                "email": to_email,
                "message": f"Itinerary successfully sent to {to_email}.",
            }
        except Exception as e:
            return {
                "ok": False,
                "status": "error",
                "email": to_email,
                "message": f"Failed to send email to {to_email}: {e}",
            }
    else:
        # Demo mode when no SMTP server is configured
        return {
            "ok": True,
            "status": "demo",
            "email": to_email,
            "message": f"Itinerary prepared and email simulated for {to_email}. (To send live emails, configure SMTP_HOST in .env)",
        }
