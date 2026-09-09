# """
# email_sender.py — sends the punch-notification email over your company SMTP
# server. Credentials are read from Streamlit secrets (.streamlit/secrets.toml),
# never hardcoded.
# """

# import smtplib
# import ssl
# from email.mime.application import MIMEApplication
# from email.mime.multipart import MIMEMultipart
# from email.mime.text import MIMEText

# import streamlit as st


# def send_email(to_addrs, subject, body_text, body_html, attachment_bytes,
#                attachment_filename, cc_addrs=None):
#     cc_addrs = cc_addrs or []
#     smtp_cfg = st.secrets["smtp"]
#     host = smtp_cfg["host"]
#     port = int(smtp_cfg["port"])
#     username = smtp_cfg["username"]
#     password = smtp_cfg["password"]
#     from_addr = smtp_cfg.get("from_email", username)
#     use_tls = smtp_cfg.get("use_tls", True)

#     msg = MIMEMultipart("mixed")
#     msg["From"] = from_addr
#     msg["To"] = ", ".join(to_addrs)
#     if cc_addrs:
#         msg["Cc"] = ", ".join(cc_addrs)
#     msg["Subject"] = subject

#     alt = MIMEMultipart("alternative")
#     alt.attach(MIMEText(body_text, "plain"))
#     if body_html:
#         alt.attach(MIMEText(body_html, "html"))
#     msg.attach(alt)

#     if attachment_bytes is not None:
#         part = MIMEApplication(attachment_bytes, Name=attachment_filename)
#         part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
#         msg.attach(part)

#     all_recipients = list(to_addrs) + list(cc_addrs)

#     if port == 465:
#         context = ssl.create_default_context()
#         with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
#             server.login(username, password)
#             server.sendmail(from_addr, all_recipients, msg.as_string())
#     else:
#         with smtplib.SMTP(host, port, timeout=30) as server:
#             server.ehlo()
#             if use_tls:
#                 context = ssl.create_default_context()
#                 server.starttls(context=context)
#                 server.ehlo()
#             server.login(username, password)
#             server.sendmail(from_addr, all_recipients, msg.as_string())


"""
email_sender.py — sends the punch-notification email over SMTP. Credentials
are read from Streamlit secrets (.streamlit/secrets.toml), never hardcoded.

Supports multiple NAMED SMTP accounts (secrets.toml has [smtp.<account>]
sections) because different plants can legitimately need to send FROM
different mailboxes — e.g. one plant's notifications go out from a company
mailbox, another's from a different provider's account entirely. Each
entity picks which account to use via its `smtp_account` field; if unset,
falls back to the "default" account.
"""

import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import streamlit as st

DEFAULT_ACCOUNT = "default"


class SmtpAccountNotConfigured(Exception):
    pass


def get_account_config(account: str = DEFAULT_ACCOUNT):
    account = account or DEFAULT_ACCOUNT
    try:
        smtp_root = st.secrets["smtp"]
    except (KeyError, FileNotFoundError):
        raise SmtpAccountNotConfigured(
            "No [smtp] section found in secrets.toml at all."
        )
    if account not in smtp_root:
        available = ", ".join(smtp_root.keys()) or "(none)"
        raise SmtpAccountNotConfigured(
            f"SMTP account '{account}' is not configured in secrets.toml. "
            f"Available accounts: {available}"
        )
    return smtp_root[account]


def list_configured_accounts():
    try:
        return list(st.secrets["smtp"].keys())
    except (KeyError, FileNotFoundError):
        return []


def send_email(to_addrs, subject, body_text, body_html, attachment_bytes,
               attachment_filename, cc_addrs=None, account: str = DEFAULT_ACCOUNT):
    cc_addrs = cc_addrs or []
    smtp_cfg = get_account_config(account)

    host = smtp_cfg["host"]
    port = int(smtp_cfg["port"])
    username = smtp_cfg["username"]
    password = smtp_cfg["password"]
    from_addr = smtp_cfg.get("from_email", username)
    use_tls = smtp_cfg.get("use_tls", True)

    msg = MIMEMultipart("mixed")
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_addrs)
    if cc_addrs:
        msg["Cc"] = ", ".join(cc_addrs)
    msg["Subject"] = subject

    alt = MIMEMultipart("alternative")
    alt.attach(MIMEText(body_text, "plain"))
    if body_html:
        alt.attach(MIMEText(body_html, "html"))
    msg.attach(alt)

    if attachment_bytes is not None:
        part = MIMEApplication(attachment_bytes, Name=attachment_filename)
        part["Content-Disposition"] = f'attachment; filename="{attachment_filename}"'
        msg.attach(part)

    all_recipients = list(to_addrs) + list(cc_addrs)

    if port == 465:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
            server.login(username, password)
            server.sendmail(from_addr, all_recipients, msg.as_string())
    else:
        with smtplib.SMTP(host, port, timeout=30) as server:
            server.ehlo()
            if use_tls:
                context = ssl.create_default_context()
                server.starttls(context=context)
                server.ehlo()
            server.login(username, password)
            server.sendmail(from_addr, all_recipients, msg.as_string())