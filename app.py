"""
EMSYS MAIL AUTOMATION PORTAL — upload a schedule CSV, auto-detect the plant/
entity (matched primarily by POS Name), and email the configured To/Cc
recipients with the file attached. No time-of-day restriction — upload and
send whenever you like, and no data-validation gate — the file is used
exactly as uploaded.

UI is styled to match the look of the real NRLDC/WRLDC scheduling portal
(dark dashboard, top status bar, sidebar nav, boxed tab card) — see theme.py.
"""

from datetime import datetime, date

import streamlit as st

import db
import csv_parser
import email_sender
import seed_south_region
import theme

st.set_page_config(
    page_title="EMSYS MAIL AUTOMATION PORTAL",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)
db.init_db()
theme.inject_css()

if "sent_files" not in st.session_state:
    st.session_state.sent_files = set()
if "submitted_files" not in st.session_state:
    st.session_state.submitted_files = set()
if "page" not in st.session_state:
    st.session_state.page = "Home"
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False


class _SafeFormatDict(dict):
    """Used with str.format_map so a template referencing a placeholder that
    no longer exists in ctx (e.g. an old saved template still using
    {blocks_table} from before block-time logic was removed) renders as an
    empty string instead of raising KeyError."""
    def __missing__(self, key):
        return ""


def sent_today_count():
    rows = db.list_send_log(limit=500)
    today_str = date.today().isoformat()
    return sum(1 for r in rows if r["status"] == "sent" and (r["sent_at"] or "").startswith(today_str))


def resolve_entity(parsed):
    """
    PRIMARY: match by POS Name. Some scheduling entities intentionally
    bundle multiple distinct plants under one 'Scheduling entity' code (a
    QCA aggregating several solar plants, for example) — POS Name is what
    actually tells them apart, so it's checked first, not entity_key.

    SECONDARY (hint only): if entity_key is already registered elsewhere
    (a different POS bundle under the same scheduling entity), surface that
    as an informational note, but still require the setup form since this
    specific POS Name isn't registered under anything yet.
    """
    for pos_name in parsed.pos_names:
        candidate = db.get_entity_by_pos_name(pos_name)
        if candidate is not None:
            return candidate, None

    hint = None
    existing_by_key = db.get_entity_by_key(parsed.entity_key)
    if existing_by_key is not None:
        hint = (
            f"Note: Scheduling entity '{parsed.entity_key}' is already registered "
            f"for a different plant ('{existing_by_key['display_name']}'), but none "
            f"of this file's POS Name(s) {parsed.pos_names} match it — treating this "
            f"as a separate plant that needs its own setup below."
        )
    return None, hint


def get_unregistered_pos_names(entity, parsed):
    """
    Returns the list of POS Names present in the uploaded file that are NOT
    yet registered against this entity. If the entity itself doesn't exist,
    or has no POS Name configured yet, every POS Name in the file counts as
    unregistered — this is what triggers the setup/confirmation form again,
    even for an entity_key that's already known.
    """
    if not entity or not entity["pos_name"]:
        return list(parsed.pos_names)
    configured = [p.strip().lower() for p in entity["pos_name"].split(",") if p.strip()]
    return [p for p in parsed.pos_names if p.lower() not in configured]


# ---------------------------------------------------------------- Home

def render_home_page():
    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    st.markdown(
        """<div class="pp-hero">
             <h1>⚡ EMSYS Mail Automation Portal</h1>
             <p>This portal automates the part of schedule punching that used to be manual:
             once you upload the schedule CSV you already punch on NRLDC/WRLDC, it detects
             which plant it belongs to, works out exactly which two 15-minute blocks you're
             revising right now, protects every other block from accidental changes, and
             emails the right recipients with the corrected file attached — automatically.</p>
           </div>""",
        unsafe_allow_html=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("How to navigate this portal")
    steps = [
        ("1", "Upload & Send", "Upload a schedule CSV here. The portal reads the "
         "'Scheduling entity' and POS Name from the file and shows you exactly what "
         "will be sent before anything goes out. If the plant (POS Name) hasn't been "
         "registered yet, you'll be asked to confirm/fill in its details (recipients, "
         "sending account, templates) right there."),
        ("2", "Manage Entities", "Admin-only. Add or edit plants/entities, their POS "
         "Name(s) and Energy Type, their 'To'/'Cc' recipient lists, and the email "
         "subject/body templates used when sending. Protected by an admin password."),
        ("3", "Send Log", "Shows every file punched today with a one-click download, "
         "plus a full region-wise, searchable File Archive of everything ever sent — "
         "nothing is ever auto-deleted."),
    ]
    for num, title, desc in steps:
        st.markdown(
            f"""<div class="pp-doc-step">
                  <div class="num">{num}</div>
                  <div>
                    <div class="title">{title}</div>
                    <div class="desc">{desc}</div>
                  </div>
                </div>""",
            unsafe_allow_html=True,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("How entity/plant matching works")
    st.markdown(
        "- Every upload is matched primarily by **POS Name**, not just the "
        "'Scheduling entity' field — some scheduling entities (e.g. a QCA code) "
        "bundle several independent plants together, and POS Name is what "
        "actually tells them apart.\n"
        "- If a POS Name hasn't been registered before, you'll be asked to "
        "confirm/fill in that plant's recipients and template — even if the "
        "'Scheduling entity' code is already known for a *different* plant.\n"
        "- There's no time-of-day restriction and no data-validation gate — "
        "upload and send whenever you like, exactly as the file is."
    )
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Upload & Send

def render_upload_tab():
    uploaded = st.file_uploader("Schedule CSV", type=["csv"], label_visibility="collapsed")
    if uploaded is None:
        return

    file_key = f"{uploaded.name}:{uploaded.size}"
    raw_bytes = uploaded.getvalue()

    try:
        parsed = csv_parser.parse_schedule_csv(raw_bytes, uploaded.name)
    except ValueError as e:
        st.error(str(e))
        return

    now = datetime.now()

    # ---- read-only "form" mirroring the real portal's field layout ----
    c1, c2, c3 = st.columns(3)
    with c1: theme.field_chip("Revision Type", parsed.revision)
    with c2: theme.field_chip("Scheduling Entity", parsed.entity_key)
    with c3: theme.field_chip("Date", parsed.date_str)

    c4, c5 = st.columns(2)
    with c4: theme.field_chip("POS Name", ", ".join(parsed.pos_names))
    with c5: theme.field_chip("Energy Type", ", ".join(parsed.energy_types))

    st.markdown('<span class="pp-mandatory">* All fields above are read-only — detected from the file</span>', unsafe_allow_html=True)

    if st.button("Submit", type="primary", key=f"submit_{file_key}"):
        st.session_state.submitted_files.add(file_key)

    if file_key not in st.session_state.submitted_files:
        return

    st.divider()

    entity, resolve_note = resolve_entity(parsed)
    if resolve_note:
        st.info(resolve_note)

    # ---- POS Name registration check: even if the entity itself is already
    # known (matched by entity_key), any POS Name we haven't seen registered
    # against it before triggers the setup form again, so a human confirms
    # the mapping before anything gets sent. ----
    unregistered_pos = get_unregistered_pos_names(entity, parsed)
    needs_setup = (entity is None) or bool(unregistered_pos)

    # No time-window logic anymore — the file is used exactly as uploaded,
    # with no restriction on which blocks/rows can differ from anything
    # previously sent. Upload whenever you like.
    output_bytes = raw_bytes

    if needs_setup:
        if entity is None:
            st.warning(
                f"'{parsed.entity_key}' is not configured yet. Fill in the details "
                f"below and it will be sent immediately after saving."
            )
        else:
            st.warning(
                f"New POS Name(s) detected for '{entity['display_name']}': "
                f"**{', '.join(unregistered_pos)}**. Confirm/update this entity's "
                f"configuration below before it gets sent."
            )

        existing_to = [r["email"] for r in db.list_recipients(entity["id"], kind="to")] if entity else []
        existing_cc = [r["email"] for r in db.list_recipients(entity["id"], kind="cc")] if entity else []

        merged_pos_list = []
        if entity and entity["pos_name"]:
            merged_pos_list.extend(p.strip() for p in entity["pos_name"].split(",") if p.strip())
        for p in parsed.pos_names:
            if p not in merged_pos_list:
                merged_pos_list.append(p)

        with st.form("entity_setup_inline"):
            display_name = st.text_input(
                "Display name", value=entity["display_name"] if entity else parsed.entity_key
            )
            region = st.text_input(
                "Region (e.g. NRLDC / WRLDC)", value=(entity["region"] if entity and entity["region"] else "")
            )
            pos_name = st.text_input(
                "POS Name(s) — comma-separated if more than one",
                value=", ".join(merged_pos_list),
            )
            energy_type = st.text_input(
                "Energy Type(s)",
                value=(entity["energy_type"] if entity and entity["energy_type"] else ", ".join(parsed.energy_types)),
            )
            smtp_account = st.text_input(
                "Sending account (matches a [smtp.<name>] section in secrets.toml)",
                value=(entity["smtp_account"] if entity and entity["smtp_account"] else email_sender.DEFAULT_ACCOUNT),
                help="Leave as 'default' unless this plant's emails need to go out "
                     "from a different mailbox/provider than the rest.",
            )
            to_text = st.text_area(
                "'To' recipient email(s) — one per line", value="\n".join(existing_to), height=90
            )
            cc_text = st.text_area(
                "'Cc' recipient email(s) — one per line (optional)", value="\n".join(existing_cc), height=70
            )
            subject_template = st.text_input(
                "Email subject template",
                value=(entity["subject_template"] if entity else db.DEFAULT_SUBJECT),
            )
            body_template = st.text_area(
                "Email body template",
                value=(entity["body_template"] if entity else db.DEFAULT_BODY),
                height=220,
            )
            st.caption(
                "Placeholders available: {entity_key} {display_name} {date} "
                "{revision} {punch_time} {filename}"
            )
            submit_label = "Update entity & send now" if entity else "Save entity & send now"
            submitted = st.form_submit_button(submit_label)

        if submitted:
            to_emails = [r.strip() for r in to_text.splitlines() if r.strip()]
            cc_emails = [r.strip() for r in cc_text.splitlines() if r.strip()]
            if not to_emails:
                st.error("Add at least one 'To' recipient email.")
                return
            if entity:
                db.update_entity_meta(entity["id"], display_name, region, pos_name, energy_type, smtp_account)
                db.update_entity_templates(entity["id"], subject_template, body_template)
                db.replace_recipients(entity["id"], to_emails, cc_emails)
                entity = db.get_entity_by_id(entity["id"])
            else:
                entity_id = db.create_entity(
                    entity_key=parsed.entity_key,
                    display_name=display_name,
                    region=region,
                    to_emails=to_emails,
                    cc_emails=cc_emails,
                    pos_name=pos_name,
                    energy_type=energy_type,
                    smtp_account=smtp_account,
                    subject_template=subject_template,
                    body_template=body_template,
                )
                entity = db.get_entity_by_id(entity_id)
        else:
            return

    to_recipients = [r["email"] for r in db.list_recipients(entity["id"], kind="to")]
    cc_recipients = [r["email"] for r in db.list_recipients(entity["id"], kind="cc")]
    if not to_recipients:
        st.error(
            f"'{entity['display_name']}' has no 'To' recipients configured. "
            f"Add one under 'Manage Entities' first."
        )
        return

    ctx = {
        "entity_key": parsed.entity_key,
        "display_name": entity["display_name"],
        "date": parsed.date_str,
        "revision": parsed.revision,
        "punch_time": now.strftime("%d-%m-%Y %H:%M"),
        "filename": uploaded.name,
    }
    # format_map with a "missing key -> empty string" fallback, not plain
    # .format(**ctx): an entity saved before this change might still have
    # {blocks_table} in its stored template, and that placeholder no longer
    # exists in ctx now that block-time logic is gone. Without this, sending
    # would crash with a KeyError instead of just dropping the placeholder.
    subject = entity["subject_template"].format_map(_SafeFormatDict(ctx))
    body_text = entity["body_template"].format_map(_SafeFormatDict(ctx))
    # These are just the prefill values for the editable review fields below —
    # the actual values used at send time come from what's in those fields
    # (which may have been edited), not from these template-rendered defaults.

    st.markdown("##### Review & edit before sending")
    st.caption(
        f"Prefilled from this entity's saved template and recipients — edit anything "
        f"below for just this email. It won't change what's saved under Manage Entities. "
        f"Sending account: **{entity['smtp_account'] or email_sender.DEFAULT_ACCOUNT}**"
    )
    edited_subject = st.text_input("Subject", value=subject, key=f"edit_subject_{file_key}")
    edited_body = st.text_area("Body", value=body_text, height=220, key=f"edit_body_{file_key}")
    edited_to_text = st.text_area(
        "To recipients — one per line", value="\n".join(to_recipients),
        height=80, key=f"edit_to_{file_key}",
    )
    edited_cc_text = st.text_area(
        "Cc recipients — one per line (optional)", value="\n".join(cc_recipients),
        height=70, key=f"edit_cc_{file_key}",
    )

    if file_key in st.session_state.sent_files:
        st.success("Already sent for this file in this session.")
        return

    if st.button("📧 Send email now", type="primary", key=f"send_{file_key}"):
        final_to = [r.strip() for r in edited_to_text.splitlines() if r.strip()]
        final_cc = [r.strip() for r in edited_cc_text.splitlines() if r.strip()]
        final_subject = edited_subject.strip()
        final_body_text = edited_body
        final_body_html = "<pre style='font-family:inherit'>" + final_body_text + "</pre>"

        if not final_to:
            st.error("At least one 'To' recipient is required.")
            return

        all_recipients = final_to + final_cc
        try:
            email_sender.send_email(
                to_addrs=final_to,
                cc_addrs=final_cc,
                subject=final_subject,
                body_text=final_body_text,
                body_html=final_body_html,
                attachment_bytes=output_bytes,
                attachment_filename=uploaded.name,
                account=entity["smtp_account"] or email_sender.DEFAULT_ACCOUNT,
            )
            db.log_send(
                entity_key=parsed.entity_key,
                display_name=entity["display_name"],
                filename=uploaded.name,
                block1_num=None,
                block2_num=None,
                recipients=all_recipients,
                status="sent",
                file_bytes=output_bytes,
                entity_id=entity["id"],
            )
            st.session_state.sent_files.add(file_key)
            st.success(f"Email sent to {', '.join(all_recipients)}")
        except Exception as e:
            db.log_send(
                entity_key=parsed.entity_key,
                display_name=entity["display_name"],
                filename=uploaded.name,
                block1_num=None,
                block2_num=None,
                recipients=all_recipients,
                status="failed",
                error=str(e),
                entity_id=entity["id"],
            )
            st.error(f"Failed to send: {e}")


def render_upload_page():
    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("Punch Upload")
    render_upload_tab()
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Manage Entities (admin only)

def render_admin_login():
    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("Admin Login Required")
    st.info("Manage Entities is admin-only. Enter the admin password to continue.")
    with st.form("admin_login_form"):
        pwd = st.text_input("Admin password", type="password")
        submitted = st.form_submit_button("Login")
    if submitted:
        try:
            correct = st.secrets["admin"]["password"]
        except (KeyError, FileNotFoundError):
            st.error(
                "No admin password configured. Add [admin] password = \"...\" "
                "to your secrets.toml first."
            )
            st.markdown('</div>', unsafe_allow_html=True)
            return
        if pwd == correct:
            st.session_state.is_admin = True
            st.rerun()
        else:
            st.error("Incorrect password.")
    st.markdown('</div>', unsafe_allow_html=True)


def render_manage_page():
    if not st.session_state.is_admin:
        render_admin_login()
        return

    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("Manage Entities & Recipients (Admin)")

    if st.button("🔒 Log out of admin"):
        st.session_state.is_admin = False
        st.rerun()

    with st.expander("💾 Backup & Restore (important if hosted somewhere without guaranteed persistent storage)"):
        st.caption(
            "Some free hosting platforms can reset the app's local storage on redeploys "
            "or after long idle periods. Download a backup regularly, and keep it "
            "somewhere safe so you can restore everything in one click if that happens."
        )
        if db.DB_PATH.exists():
            backup_bytes = db.DB_PATH.read_bytes()
            st.download_button(
                "⬇ Download full database backup",
                data=backup_bytes,
                file_name=f"portal_backup_{date.today().isoformat()}.db",
            )
        restore_file = st.file_uploader("Restore from a backup file", type=["db"], key="restore_upload")
        if restore_file is not None:
            st.warning("This will overwrite everything currently in the database.")
            if st.button("⚠️ Confirm restore"):
                db.DB_PATH.write_bytes(restore_file.getvalue())
                st.success("Database restored.")
                st.rerun()

        st.divider()
        st.caption(
            "Quick recovery for the South region setup specifically — safe to click "
            "even if it's already configured (updates instead of duplicating)."
        )
        if st.button("🌱 Seed/restore South region entities"):
            messages = seed_south_region.main()
            for m in messages:
                st.write("•", m)
            st.rerun()

    entities = db.list_entities()
    if not entities:
        st.info("No entities configured yet. They'll appear here once added "
                 "(either manually below, or automatically on first upload).")

    with st.expander("➕ Add a new entity manually"):
        with st.form("add_entity_form"):
            entity_key = st.text_input(
                "Entity key (must match the 'Scheduling entity' value in the CSV exactly)"
            )
            display_name = st.text_input("Display name")
            region = st.text_input("Region (e.g. NRLDC / WRLDC)")
            pos_name = st.text_input("POS Name(s) — comma-separated if more than one")
            energy_type = st.text_input("Energy Type(s) — e.g. SOLAR, WIND")
            smtp_account = st.text_input(
                "Sending account (matches a [smtp.<name>] section in secrets.toml)",
                value=email_sender.DEFAULT_ACCOUNT,
            )
            to_text = st.text_area("'To' recipient email(s) — one per line", height=90)
            cc_text = st.text_area("'Cc' recipient email(s) — one per line (optional)", height=70)
            subject_template = st.text_input("Email subject template", value=db.DEFAULT_SUBJECT)
            body_template = st.text_area("Email body template", value=db.DEFAULT_BODY, height=220)
            submitted = st.form_submit_button("Create entity")
        if submitted:
            if not entity_key or not display_name:
                st.error("Entity key and display name are required.")
            else:
                to_emails = [r.strip() for r in to_text.splitlines() if r.strip()]
                cc_emails = [r.strip() for r in cc_text.splitlines() if r.strip()]
                db.create_entity(entity_key, display_name, region, to_emails, cc_emails,
                                  pos_name, energy_type, smtp_account, subject_template, body_template)
                st.success(f"Entity '{display_name}' created.")
                st.rerun()

    for entity in entities:
        pos_label = entity["pos_name"] or "no POS Name registered"
        with st.expander(f"{entity['display_name']}  ·  POS: {pos_label}  ·  key: {entity['entity_key']}"):
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Details**")
                new_display_name = st.text_input(
                    "Display name", value=entity["display_name"], key=f"dn_{entity['id']}"
                )
                new_region = st.text_input(
                    "Region", value=entity["region"] or "", key=f"rg_{entity['id']}"
                )
                new_pos_name = st.text_input(
                    "POS Name(s)", value=entity["pos_name"] or "", key=f"pos_{entity['id']}"
                )
                new_energy_type = st.text_input(
                    "Energy Type(s)", value=entity["energy_type"] or "", key=f"etype_{entity['id']}"
                )
                new_smtp_account = st.text_input(
                    "Sending account (matches a [smtp.<name>] section in secrets.toml)",
                    value=entity["smtp_account"] or email_sender.DEFAULT_ACCOUNT,
                    key=f"smtp_{entity['id']}",
                )
                if st.button("Update details", key=f"upd_meta_{entity['id']}"):
                    db.update_entity_meta(entity["id"], new_display_name, new_region,
                                           new_pos_name, new_energy_type, new_smtp_account)
                    st.success("Updated.")
                    st.rerun()

                st.markdown("**Recipients**")
                for kind_label, kind in [("To", "to"), ("Cc", "cc")]:
                    st.caption(kind_label)
                    recipients = db.list_recipients(entity["id"], kind=kind)
                    if not recipients:
                        st.caption("— none —")
                    for r in recipients:
                        rc1, rc2 = st.columns([4, 1])
                        rc1.write(r["email"])
                        if rc2.button("Remove", key=f"rm_{r['id']}"):
                            db.remove_recipient(r["id"])
                            st.rerun()
                    ac1, ac2 = st.columns([3, 1])
                    new_email = ac1.text_input(
                        f"Add {kind_label} recipient", key=f"new_email_{kind}_{entity['id']}",
                        label_visibility="collapsed", placeholder=f"Add {kind_label} email"
                    )
                    if ac2.button("Add", key=f"add_email_{kind}_{entity['id']}"):
                        if new_email.strip():
                            db.add_recipient(entity["id"], new_email.strip(), kind=kind)
                            st.rerun()

                if st.button("🗑 Delete this entity", key=f"del_{entity['id']}"):
                    db.delete_entity(entity["id"])
                    st.rerun()

            with col2:
                st.markdown("**Email template**")
                st.caption(
                    "Placeholders: {entity_key} {display_name} {date} {revision} "
                    "{punch_time} {filename}"
                )
                subj = st.text_input(
                    "Subject", value=entity["subject_template"], key=f"subj_{entity['id']}"
                )
                body = st.text_area(
                    "Body", value=entity["body_template"], height=260, key=f"body_{entity['id']}"
                )
                if st.button("Modify template", key=f"modify_{entity['id']}"):
                    db.update_entity_templates(entity["id"], subj, body)
                    st.success("Template updated.")

    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- Send Log

def _split_sent_at(rows_as_dicts):
    """Splits the combined 'sent_at' ISO timestamp into separate 'Date' and
    'Time' keys for display — easier to scan/sort than one combined column."""
    out = []
    for r in rows_as_dicts:
        r = dict(r)
        sent_at = r.pop("sent_at", None) or ""
        if "T" in sent_at:
            d, t = sent_at.split("T", 1)
        else:
            d, t = sent_at, ""
        r["date"] = d
        r["time"] = t
        out.append(r)
    return out


def render_log_page():
    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("Today's Punched Files")
    today_files = db.list_today_files()
    if not today_files:
        st.info("No files punched yet today.")
    else:
        for row in today_files:
            date_part, _, time_part = (row["sent_at"] or "").partition("T")
            fc1, fc2 = st.columns([5, 1])
            with fc1:
                st.markdown(
                    f"""<div class="pp-file-row">
                          <div>
                            <strong>{row['display_name']}</strong> ({row['entity_key']}) —
                            <span style="color:var(--text-secondary);">{date_part} {time_part}</span>
                          </div>
                        </div>""",
                    unsafe_allow_html=True,
                )
            with fc2:
                if row["file_blob"]:
                    st.download_button(
                        "⬇ Download", data=row["file_blob"], file_name=row["filename"],
                        key=f"dl_{row['id']}", use_container_width=True,
                    )
    st.markdown('</div>', unsafe_allow_html=True)

    # ---- File Archive: the persistent, region-aware, any-date lookup ----
    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("📁 File Archive — search anytime, region-wise")
    st.caption(
        "Every file ever successfully sent stays here — nothing is deleted. "
        "Filter by region so different regions' files never mix together."
    )

    regions = db.list_regions()
    ac1, ac2, ac3 = st.columns([1.2, 1.6, 1.2])
    with ac1:
        region_choice = st.selectbox("Region", ["All regions"] + regions, key="archive_region")
    with ac2:
        search_text = st.text_input(
            "Search (filename, plant name, or scheduling entity)", key="archive_search",
            placeholder="e.g. AvaadaSolar, PVG_RES_QCA, 08-09-2026...",
        )
    with ac3:
        archive_date_mode = st.selectbox(
            "Date", ["Any date", "Single date", "Date range"], key="archive_date_mode"
        )

    archive_date_from = archive_date_to = None
    if archive_date_mode == "Single date":
        picked = st.date_input("Date", value=date.today(), key="archive_single_date")
        archive_date_from = picked.isoformat()
    elif archive_date_mode == "Date range":
        rc1, rc2 = st.columns(2)
        with rc1:
            range_start = st.date_input("From", value=date.today(), key="archive_from")
        with rc2:
            range_end = st.date_input("To", value=date.today(), key="archive_to")
        archive_date_from, archive_date_to = range_start.isoformat(), range_end.isoformat()

    archive_rows = db.list_file_archive(
        region=None if region_choice == "All regions" else region_choice,
        search=search_text.strip() or None,
        date_from=archive_date_from,
        date_to=archive_date_to,
        limit=300,
    )

    if not archive_rows:
        st.info("No files match this filter.")
    else:
        st.caption(f"{len(archive_rows)} file(s) found")
        for row in archive_rows:
            date_part, _, time_part = (row["sent_at"] or "").partition("T")
            region_badge = row["region"] or "no region set"
            fc1, fc2 = st.columns([5, 1])
            with fc1:
                st.markdown(
                    f"""<div class="pp-file-row">
                          <div>
                            <strong>{row['display_name']}</strong>
                            <span style="color:var(--accent);">[{region_badge}]</span>
                            — {row['filename']} —
                            <span style="color:var(--text-secondary);">{date_part} {time_part}</span>
                          </div>
                        </div>""",
                    unsafe_allow_html=True,
                )
            with fc2:
                if row["file_blob"]:
                    st.download_button(
                        "⬇ Download", data=row["file_blob"], file_name=row["filename"],
                        key=f"arc_dl_{row['id']}", use_container_width=True,
                    )
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="pp-card">', unsafe_allow_html=True)
    theme.card_header("Full Send History")

    fc1, fc2, fc3 = st.columns([1.2, 1.2, 1.2])
    with fc1:
        filter_mode = st.selectbox(
            "Filter by date", ["All dates", "Single date", "Date range"], key="log_filter_mode"
        )
    date_from = date_to = None
    if filter_mode == "Single date":
        with fc2:
            picked = st.date_input("Date", value=date.today(), key="log_filter_single")
        date_from = picked.isoformat()
    elif filter_mode == "Date range":
        with fc2:
            range_start = st.date_input("From", value=date.today(), key="log_filter_from")
        with fc3:
            range_end = st.date_input("To", value=date.today(), key="log_filter_to")
        date_from, date_to = range_start.isoformat(), range_end.isoformat()

    rows = db.list_send_log(limit=1000, date_from=date_from, date_to=date_to)
    if not rows:
        st.info("No emails sent yet." if filter_mode == "All dates" else "No emails sent on that date.")
    else:
        row_dicts = _split_sent_at([dict(r) for r in rows])
        # Reorder columns so date/time sit where sent_at used to be.
        ordered_cols = ["id", "entity_id", "entity_key", "display_name", "filename",
                        "date", "time", "block1_num", "block2_num", "recipients",
                        "status", "error"]
        ordered_cols = [c for c in ordered_cols if c in row_dicts[0]]
        st.caption(f"{len(rows)} result(s)")
        st.markdown(theme.data_table_html(row_dicts, ordered_cols), unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------------------------------------------- shell / routing

selected_page = theme.sidebar_nav(st.session_state.page)
st.session_state.page = selected_page

theme.top_bar(
    viewing_label=selected_page,
    entities_count=len(db.list_entities()),
    sent_today_count=sent_today_count(),
)

breadcrumb_clicked = theme.welcome_and_breadcrumb(
    welcome_label="Scheduling Team", current_page=selected_page
)
if breadcrumb_clicked and breadcrumb_clicked != selected_page:
    st.session_state.page = breadcrumb_clicked
    st.rerun()

if selected_page == "Home":
    render_home_page()
elif selected_page == "Upload & Send":
    render_upload_page()
elif selected_page == "Manage Entities":
    render_manage_page()
elif selected_page == "Send Log":
    render_log_page()