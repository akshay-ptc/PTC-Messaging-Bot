import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

def generate_pdf(output_path: str = "PTC_Bot_Command_Reference.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette matching PTC (Blue, Dark Navy, Teal/Cyan, Accent Orange)
    primary_color = colors.HexColor("#0B132B")      # Dark Navy
    secondary_color = colors.HexColor("#1C2541")    # Midnight Blue
    accent_blue = colors.HexColor("#1F51FF")        # Royal Electric Blue
    accent_teal = colors.HexColor("#00CECB")        # Vibrant Teal
    accent_orange = colors.HexColor("#FF6B35")      # Safety Orange
    card_bg = colors.HexColor("#F4F6F9")            # Off-white / light slate
    text_dark = colors.HexColor("#1A1A24")          # Dark Charcoal

    # Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=24,
        leading=28,
        textColor=primary_color,
        alignment=TA_LEFT
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=12,
        leading=16,
        textColor=accent_blue,
        alignment=TA_LEFT
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=19,
        textColor=primary_color,
        spaceBefore=14,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=secondary_color,
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=text_dark
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier-Bold',
        fontSize=8.5,
        leading=11,
        textColor=accent_blue
    )

    desc_style = ParagraphStyle(
        'Desc_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=text_dark
    )

    story = []

    # ==================== HEADER ====================
    story.append(Paragraph("PROP TRADERS COMMUNITY (PTC)", subtitle_style))
    story.append(Paragraph("Enterprise Discord Security & Mass DM Bot", title_style))
    story.append(Paragraph("Official Administrator & Founder Operations Manual | Version 2.0", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=accent_blue, spaceBefore=8, spaceAfter=14))

    # Security Alert Box
    alert_text = (
        "<b>RESTRICTED ACCESS:</b> All bot commands are strictly enforced for <b>Server Founder</b> and <b>Administrators</b> only. "
        "Built-in Anti-Spam protection prevents Discord token suspension through humanized jitter, HTTP 429 exponential backoff, and DM closed (50007) error isolation."
    )
    alert_table = Table(
        [[Paragraph(alert_text, body_style)]],
        colWidths=[540]
    )
    alert_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#FFF3CD")),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor("#FFEBAA")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(alert_table)
    story.append(Spacer(1, 14))

    # ==================== SECTION 1: VERIFICATION & REMINDER ====================
    story.append(Paragraph("1. Verification Onboarding & Scheduled Reminder System", h1_style))
    story.append(Paragraph(
        "Automatically sends a welcoming DM to newly joined members with the verification instructions and attached image banner. "
        "Members holding the <b>@unverified</b> role receive automated scheduled reminders (e.g. 24 hours after joining, then repeated every 24 hours).",
        body_style
    ))
    story.append(Spacer(1, 8))

    verify_data = [
        [Paragraph("<b>Command</b>", body_style), Paragraph("<b>Parameters</b>", body_style), Paragraph("<b>Description & Action</b>", body_style)],
        [
            Paragraph("<b>/verify preview</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("Sends a test preview of the verification message and banner directly to your DMs.", desc_style)
        ],
        [
            Paragraph("<b>/verify status</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("Displays active verification configuration, target channel, unverified count, and reminder cadence.", desc_style)
        ],
        [
            Paragraph("<b>/verify trigger_reminders</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("Instantly runs a reminder pass across all unverified members under safe rate-limiting.", desc_style)
        ],
    ]
    t1 = Table(verify_data, colWidths=[140, 90, 310])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t1)
    story.append(Spacer(1, 14))

    # ==================== SECTION 2: MASS DM & LINK MIRRORING ====================
    story.append(Paragraph("2. Mass DM Broadcast & Message Link Mirroring (With Yes/No Confirmation & Preview)", h1_style))
    story.append(Paragraph(
        "Dispatch text announcements with multiple image attachments or clone an existing Discord message with all attachments into members' private DMs. "
        "<b>Safety Feature:</b> Manual broadcasts automatically display an interactive preview and require clicking <b>[ Confirm & Send DMs ]</b> (Yes) or <b>[ Cancel Broadcast ]</b> (No) before any DMs are sent.",
        body_style
    ))
    story.append(Spacer(1, 8))

    dm_data = [
        [Paragraph("<b>Command</b>", body_style), Paragraph("<b>Parameters</b>", body_style), Paragraph("<b>Description & Action</b>", body_style)],
        [
            Paragraph("<b>/dm send</b>", code_style),
            Paragraph("<b>target_type:</b> all | role | user<br/><b>message:</b> text<br/><i>image_1..3:</i> file attachments", desc_style),
            Paragraph("Shows full preview & asks for Yes/No confirmation. Dispatches custom DM with up to 3 attachments to Everyone, a Role, or a specific User.", desc_style)
        ],
        [
            Paragraph("<b>/dm from_link</b>", code_style),
            Paragraph("<b>message_link:</b> URL<br/><b>target_type:</b> all | role | user<br/><i>role:</i> optional<br/><i>user:</i> optional", desc_style),
            Paragraph("Shows full preview & asks for Yes/No confirmation. Clones any server announcement by URL (text, embeds, downloaded attachments) into DMs.", desc_style)
        ],
    ]
    t2 = Table(dm_data, colWidths=[130, 140, 270])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t2)
    story.append(Spacer(1, 14))

    # ==================== SECTION 3: CAMPAIGN CRUD ====================
    story.append(Paragraph("3. Campaign Management & Queue Control (CRUD)", h1_style))
    story.append(Paragraph(
        "Monitor live deliveries in real-time, pause active campaigns if needed, resume them, or cancel pending messages.",
        body_style
    ))
    story.append(Spacer(1, 8))

    camp_data = [
        [Paragraph("<b>Command</b>", body_style), Paragraph("<b>Parameters</b>", body_style), Paragraph("<b>Description & Action</b>", body_style)],
        [
            Paragraph("<b>/campaign list</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("<b>[READ]</b> Lists recent broadcast campaigns with real-time status and delivery percentages.", desc_style)
        ],
        [
            Paragraph("<b>/campaign status</b>", code_style),
            Paragraph("<b>campaign_id:</b> int", desc_style),
            Paragraph("<b>[READ]</b> Shows detailed breakdown of delivered, blocked DMs (50007), failed, and remaining queue items.", desc_style)
        ],
        [
            Paragraph("<b>/campaign pause</b>", code_style),
            Paragraph("<b>campaign_id:</b> int", desc_style),
            Paragraph("<b>[UPDATE]</b> Halts an ongoing DM broadcast instantly.", desc_style)
        ],
        [
            Paragraph("<b>/campaign resume</b>", code_style),
            Paragraph("<b>campaign_id:</b> int", desc_style),
            Paragraph("<b>[UPDATE]</b> Resumes a paused campaign safely.", desc_style)
        ],
        [
            Paragraph("<b>/campaign cancel</b>", code_style),
            Paragraph("<b>campaign_id:</b> int", desc_style),
            Paragraph("<b>[DELETE]</b> Cancels campaign and purges pending queue entries.", desc_style)
        ],
    ]
    t3 = Table(camp_data, colWidths=[130, 110, 300])
    t3.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t3)

    story.append(PageBreak())

    # ==================== SECTION 4: CONFIGURATION & TEMPLATES CRUD ====================
    story.append(Paragraph("4. Server Configuration, Blacklist & Reusable Templates (CRUD)", h1_style))
    story.append(Paragraph(
        "Manage roles, verification channels, custom reusable templates, and user opt-outs.",
        body_style
    ))
    story.append(Spacer(1, 8))

    cfg_data = [
        [Paragraph("<b>Command</b>", body_style), Paragraph("<b>Parameters</b>", body_style), Paragraph("<b>Description & Action</b>", body_style)],
        [
            Paragraph("<b>/config view</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("<b>[READ]</b> View current verification channel, roles, delays, and message template.", desc_style)
        ],
        [
            Paragraph("<b>/config set</b>", code_style),
            Paragraph("verification_channel, unverified_role, verified_role, initial_delay_hours, repeat_interval_hours, reminder_enabled", desc_style),
            Paragraph("<b>[UPDATE]</b> Configure role IDs, target channels, and schedule cadence (e.g. 24h delay, 24h repeat).", desc_style)
        ],
        [
            Paragraph("<b>/config set_message</b>", code_style),
            Paragraph("<b>message:</b> text", desc_style),
            Paragraph("<b>[UPDATE]</b> Set custom verification reminder template text with {channel_id} token.", desc_style)
        ],
        [
            Paragraph("<b>/blacklist add</b>", code_style),
            Paragraph("<b>user:</b> Member, <i>reason:</i> text", desc_style),
            Paragraph("<b>[CREATE]</b> Exclude a member from receiving all automated and broadcast DMs.", desc_style)
        ],
        [
            Paragraph("<b>/blacklist remove</b>", code_style),
            Paragraph("<b>user:</b> Member", desc_style),
            Paragraph("<b>[DELETE]</b> Remove user from the opt-out blacklist.", desc_style)
        ],
        [
            Paragraph("<b>/blacklist list</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("<b>[READ]</b> View all blacklisted members and reasons.", desc_style)
        ],
        [
            Paragraph("<b>/template create</b>", code_style),
            Paragraph("<b>name:</b> str, <b>content:</b> str", desc_style),
            Paragraph("<b>[CREATE]</b> Save reusable announcement/marketing templates in SQLite.", desc_style)
        ],
        [
            Paragraph("<b>/template get</b>", code_style),
            Paragraph("<b>name:</b> str", desc_style),
            Paragraph("<b>[READ]</b> Retrieve a saved template body.", desc_style)
        ],
        [
            Paragraph("<b>/template list</b>", code_style),
            Paragraph("None", desc_style),
            Paragraph("<b>[READ]</b> List all saved templates.", desc_style)
        ],
        [
            Paragraph("<b>/template delete</b>", code_style),
            Paragraph("<b>name:</b> str", desc_style),
            Paragraph("<b>[DELETE]</b> Remove a saved template.", desc_style)
        ],
    ]
    t4 = Table(cfg_data, colWidths=[130, 140, 270])
    t4.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
        ('PADDING', (0,0), (-1,-1), 4.5),
    ]))
    story.append(t4)
    story.append(Spacer(1, 14))

    # ==================== SECTION 5: ANTI-SPAM PROTECTION ====================
    story.append(Paragraph("5. Discord Anti-Spam & Rate-Limit Protection Mechanics", h1_style))
    spam_info = [
        [
            Paragraph("<b>Heuristic Protection</b>", h2_style),
            Paragraph("<b>How It Keeps the Bot Safe from Discord Bans</b>", h2_style)
        ],
        [
            Paragraph("<b>Humanized Jitter Delay</b>", body_style),
            Paragraph("Applies a randomized 3.0 to 6.0 second wait between each individual DM. Prevents sudden traffic bursts that trigger Discord's spam bot filters.", body_style)
        ],
        [
            Paragraph("<b>Batch Cool-Down Breaks</b>", body_style),
            Paragraph("After every 20 DMs dispatched, the bot pauses for a 25-second cool-down breather before continuing the queue.", body_style)
        ],
        [
            Paragraph("<b>HTTP 429 Exponential Backoff</b>", body_style),
            Paragraph("If Discord returns a 429 rate limit code, the worker extracts the exact `retry_after` parameter, pauses safely for that duration + 2s buffer, then resumes without dropping messages.", body_style)
        ],
        [
            Paragraph("<b>Error 50007 Isolation (Closed DMs)</b>", body_style),
            Paragraph("When users have closed DMs or blocked the bot, it logs 'Blocked DM' without retrying or causing gateway abuse flags.", body_style)
        ],
        [
            Paragraph("<b>Circuit Breaker Fail-Safe</b>", body_style),
            Paragraph("If 5 consecutive hard network or permission errors occur, the bot auto-pauses the campaign to prevent spamming failed sockets.", body_style)
        ],
    ]
    t5 = Table(spam_info, colWidths=[170, 370])
    t5.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), secondary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#D0D7DE")),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, card_bg]),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(t5)
    story.append(Spacer(1, 14))

    # ==================== SECTION 6: 24/7 HOSTING GUIDE ====================
    story.append(Paragraph("6. 24/7 Free Hosting Setup (Render + UptimeRobot)", h1_style))
    steps_text = (
        "<b>Step 1: Discord Developer Portal Setup</b><br/>"
        "• Go to <font color='#1F51FF'>discord.com/developers/applications</font>, select your Bot.<br/>"
        "• Under <b>Bot -> Privileged Gateway Intents</b>, ENABLE: <b>SERVER MEMBERS INTENT</b> and <b>MESSAGE CONTENT INTENT</b>.<br/>"
        "• Under <b>Installation</b>, ensure bot has <b>Send Messages, Attach Files, Read Messages, Administrator</b> permissions.<br/><br/>"
        "<b>Step 2: Deploy to Render</b><br/>"
        "• Push code to a private GitHub repository.<br/>"
        "• In <font color='#1F51FF'>render.com</font>, create a <b>New Web Service</b> pointing to your repo.<br/>"
        "• Environment: <b>Python 3</b> | Build Command: <b>pip install -r requirements.txt</b> | Start Command: <b>python bot.py</b>.<br/>"
        "• Add Environment Variables: <b>DISCORD_TOKEN</b>, <b>FOUNDER_ID</b>, <b>ADMIN_ROLE_ID</b>, <b>PORT=8080</b>.<br/><br/>"
        "<b>Step 3: Keep-Alive 24/7 with UptimeRobot (Upbot)</b><br/>"
        "• Copy your Render Web Service URL: <i>https://your-bot-name.onrender.com/health</i>.<br/>"
        "• Go to <font color='#1F51FF'>uptimerobot.com</font>, create a New Monitor -> Type: <b>HTTP(s)</b>.<br/>"
        "• Monitoring Interval: <b>Every 5 minutes</b>. This pings the bot's embedded server and prevents Render free tier from sleeping!"
    )
    story.append(Paragraph(steps_text, body_style))

    # Build document
    doc.build(story)
    return output_path

if __name__ == "__main__":
    generate_pdf()

