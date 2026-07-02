from html import escape

import resend
from app.core.config import settings
from app.models.order import Order


def _order_confirmation_html(order: Order, lang: str = "fr") -> str:
    is_fr = lang == "fr"
    customer = order.customer or {}
    name = escape(customer.get("name", ""))

    greeting = f"Bonjour {name}," if is_fr else f"Hello {name},"
    subject_line = "Merci pour votre commande" if is_fr else "Thank you for your order"
    intro = (
        "Votre paiement a bien été reçu. Voici le récapitulatif de votre commande."
        if is_fr
        else "Your payment has been received. Here is a summary of your order."
    )
    order_label = "Commande" if is_fr else "Order"
    items_label = "Articles" if is_fr else "Items"
    subtotal_label = "Sous-total" if is_fr else "Subtotal"
    shipping_label = "Livraison" if is_fr else "Shipping"
    shipping_value = "Offerte" if order.shipping == 0 else f"{order.shipping:.2f} €"
    total_label = "Total" if is_fr else "Total"
    footer_text = (
        "Votre commande sera préparée et expédiée dans les meilleurs délais. À très bientôt."
        if is_fr
        else "Your order will be prepared and shipped as soon as possible. See you soon."
    )
    tagline = (
        "Maison de vêtements contemporaine. Fait avec soin, pour durer."
        if is_fr
        else "Contemporary clothing house. Made with care, made to last."
    )

    rows = ""
    for item in order.items:
        item_name = escape(item.name)
        item_color = escape(item.color)
        item_size = escape(item.size)
        rows += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #e8e0d4;font-family:Georgia,serif;font-size:15px;color:#16140f;">
            {item_name}
            <span style="font-size:12px;color:#8a8276;display:block;margin-top:2px;">
              {item_color} · {item_size} · x{item.qty}
            </span>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #e8e0d4;text-align:right;font-size:14px;color:#16140f;white-space:nowrap;">
            {item.price * item.qty:.2f} €
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="{lang}">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f6f3ee;font-family:Inter,system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f3ee;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fbf9f5;border:1px solid #e8e0d4;">

        <!-- Header -->
        <tr>
          <td style="padding:36px 48px 28px;border-bottom:1px solid #e8e0d4;text-align:center;">
            <span style="font-family:Georgia,serif;font-size:28px;font-weight:500;letter-spacing:0.42em;color:#16140f;">YFIC</span>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:40px 48px;">
            <p style="margin:0 0 8px;font-size:13px;text-transform:uppercase;letter-spacing:0.2em;color:#b07a53;">{subject_line}</p>
            <p style="margin:0 0 28px;font-family:Georgia,serif;font-size:22px;color:#16140f;font-weight:300;line-height:1.3;">{greeting}</p>
            <p style="margin:0 0 32px;font-size:14px;color:#3a352d;line-height:1.7;">{intro}</p>

            <!-- Order number -->
            <p style="margin:0 0 20px;font-size:12px;text-transform:uppercase;letter-spacing:0.18em;color:#8a8276;">
              {order_label} #{order.id}
            </p>

            <!-- Items -->
            <p style="margin:0 0 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.18em;color:#8a8276;">{items_label}</p>
            <table width="100%" cellpadding="0" cellspacing="0">
              {rows}
            </table>

            <!-- Totals -->
            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;">
              <tr>
                <td style="font-size:13px;color:#8a8276;padding:6px 0;">{subtotal_label}</td>
                <td style="font-size:13px;color:#16140f;text-align:right;padding:6px 0;">{order.subtotal:.2f} €</td>
              </tr>
              <tr>
                <td style="font-size:13px;color:#8a8276;padding:6px 0;">{shipping_label}</td>
                <td style="font-size:13px;color:#16140f;text-align:right;padding:6px 0;">{shipping_value}</td>
              </tr>
              <tr>
                <td colspan="2" style="border-top:1px solid #e8e0d4;padding-top:12px;"></td>
              </tr>
              <tr>
                <td style="font-family:Georgia,serif;font-size:16px;color:#16140f;padding:4px 0;"><strong>{total_label}</strong></td>
                <td style="font-family:Georgia,serif;font-size:16px;color:#16140f;text-align:right;padding:4px 0;"><strong>{order.total:.2f} €</strong></td>
              </tr>
            </table>

            <p style="margin:40px 0 0;font-size:14px;color:#3a352d;line-height:1.7;">{footer_text}</p>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:24px 48px;border-top:1px solid #e8e0d4;text-align:center;">
            <p style="margin:0;font-size:11px;color:#8a8276;line-height:1.6;">{tagline}</p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _admin_notification_html(order: Order) -> str:
    customer = order.customer or {}
    name = escape(customer.get("name", "—"))
    email = escape(customer.get("email", "—"))

    rows = ""
    for item in order.items:
        rows += f"""
        <tr>
          <td style="padding:8px 12px;border-bottom:1px solid #e8e0d4;font-size:14px;color:#16140f;">
            {escape(item.name)}<br>
            <span style="font-size:12px;color:#8a8276;">{escape(item.color)} · {escape(item.size)} · x{item.qty}</span>
          </td>
          <td style="padding:8px 12px;border-bottom:1px solid #e8e0d4;font-size:14px;color:#16140f;text-align:right;white-space:nowrap;">
            {item.price:.2f} € × {item.qty} = {item.price * item.qty:.2f} €
          </td>
        </tr>"""

    shipping_value = "Offerte" if order.shipping == 0 else f"{order.shipping:.2f} €"

    return f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f6f3ee;font-family:Inter,system-ui,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f6f3ee;padding:40px 16px;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;background:#fff;border:1px solid #e8e0d4;">

        <tr>
          <td style="padding:24px 36px;border-bottom:1px solid #e8e0d4;background:#16140f;">
            <span style="font-family:Georgia,serif;font-size:22px;letter-spacing:0.3em;color:#fff;">YFIC</span>
            <span style="float:right;font-size:13px;color:#ccc;line-height:1.8;">Nouvelle commande</span>
          </td>
        </tr>

        <tr>
          <td style="padding:28px 36px;">
            <p style="margin:0 0 4px;font-size:11px;text-transform:uppercase;letter-spacing:0.15em;color:#b07a53;">
              Commande #{order.id}
            </p>
            <p style="margin:0 0 24px;font-size:22px;font-family:Georgia,serif;color:#16140f;">
              {name}
            </p>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:8px;border:1px solid #e8e0d4;">
              <tr style="background:#f6f3ee;">
                <td style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#8a8276;">Client</td>
                <td style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#8a8276;text-align:right;">Email</td>
              </tr>
              <tr>
                <td style="padding:10px 12px;font-size:14px;color:#16140f;">{name}</td>
                <td style="padding:10px 12px;font-size:14px;color:#16140f;text-align:right;">{email}</td>
              </tr>
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:20px;border:1px solid #e8e0d4;">
              <tr style="background:#f6f3ee;">
                <td style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#8a8276;">Article</td>
                <td style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:0.12em;color:#8a8276;text-align:right;">Montant</td>
              </tr>
              {rows}
            </table>

            <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:16px;">
              <tr>
                <td style="font-size:13px;color:#8a8276;padding:4px 0;">Sous-total</td>
                <td style="font-size:13px;color:#16140f;text-align:right;padding:4px 0;">{order.subtotal:.2f} €</td>
              </tr>
              <tr>
                <td style="font-size:13px;color:#8a8276;padding:4px 0;">Livraison</td>
                <td style="font-size:13px;color:#16140f;text-align:right;padding:4px 0;">{shipping_value}</td>
              </tr>
              <tr>
                <td colspan="2" style="border-top:1px solid #e8e0d4;padding-top:10px;margin-top:6px;"></td>
              </tr>
              <tr>
                <td style="font-size:16px;font-family:Georgia,serif;color:#16140f;padding:4px 0;"><strong>Total</strong></td>
                <td style="font-size:16px;font-family:Georgia,serif;color:#16140f;text-align:right;padding:4px 0;"><strong>{order.total:.2f} €</strong></td>
              </tr>
            </table>
          </td>
        </tr>

        <tr>
          <td style="padding:20px 36px;border-top:1px solid #e8e0d4;text-align:center;">
            <p style="margin:0;font-size:12px;color:#8a8276;">
              Paiement confirmé — à préparer et expédier dès que possible.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


async def send_order_confirmation(order: Order) -> None:
    if not settings.resend_api_key:
        return

    resend.api_key = settings.resend_api_key
    customer = order.customer or {}
    customer_email = customer.get("email")

    if not customer_email:
        return

    resend.Emails.send({
        "from": f"{settings.store_name} <{settings.store_email}>",
        "to": [customer_email],
        "subject": f"Confirmation de commande #{order.id} — YFIC",
        "html": _order_confirmation_html(order, lang="fr"),
    })


async def send_admin_order_notification(order: Order) -> None:
    if not settings.resend_api_key or not settings.admin_email:
        return

    resend.api_key = settings.resend_api_key
    customer = order.customer or {}
    customer_name = escape(customer.get("name", "Inconnu"))

    resend.Emails.send({
        "from": f"{settings.store_name} <{settings.store_email}>",
        "to": [settings.admin_email],
        "subject": f"[YFIC] Nouvelle commande #{order.id} — {customer_name} — {order.total:.2f} €",
        "html": _admin_notification_html(order),
    })
