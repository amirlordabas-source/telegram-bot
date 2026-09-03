# -*- coding: utf-8 -*-

import os
import sqlite3
import telebot
from telebot import types


# =========================
# SETTINGS
# =========================

TOKEN = os.environ["TOKEN"]

CHANNEL_USERNAME = "@ggggggsysg"
CHANNEL_LINK = "https://t.me/ggggggsysg"

DB_NAME = "users.db"


# =========================
# BOT
# =========================

bot = telebot.TeleBot(
    TOKEN,
    parse_mode="HTML"
)


# =========================
# DATABASE
# =========================

conn = sqlite3.connect(
    DB_NAME,
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT DEFAULT '',
    full_name TEXT DEFAULT '',
    points INTEGER DEFAULT 0,
    invite_count INTEGER DEFAULT 0,
    registered INTEGER DEFAULT 0,
    referred_by INTEGER DEFAULT NULL,
    pending_referrer INTEGER DEFAULT NULL
)
""")

conn.commit()


# =========================
# MAIN KEYBOARD
# =========================

def main_keyboard():

    keyboard = types.ReplyKeyboardMarkup(
        resize_keyboard=True
    )

    keyboard.row(
        "📝 ثبت‌نام",
        "👤 حساب من"
    )

    keyboard.row(
        "🎁 معرفی دوستان"
    )

    keyboard.row(
        "🎟 قرعه‌کشی بزرگ استقلال"
    )

    return keyboard


# =========================
# SAVE USER
# =========================

def save_user(user):

    username = user.username or ""
    full_name = user.full_name or ""

    cursor.execute(
        "SELECT user_id FROM users WHERE user_id = ?",
        (user.id,)
    )

    result = cursor.fetchone()

    if result:

        cursor.execute("""
        UPDATE users
        SET username = ?,
            full_name = ?
        WHERE user_id = ?
        """, (
            username,
            full_name,
            user.id
        ))

    else:

        cursor.execute("""
        INSERT INTO users
        (
            user_id,
            username,
            full_name
        )
        VALUES (?, ?, ?)
        """, (
            user.id,
            username,
            full_name
        ))

    conn.commit()


# =========================
# CHECK MEMBERSHIP
# =========================

def is_member(user_id):

    try:

        member = bot.get_chat_member(
            CHANNEL_USERNAME,
            user_id
        )

        return member.status in [
            "member",
            "administrator",
            "creator"
        ]

    except Exception as e:

        print("Membership error:", e)
        return False


# =========================
# MEMBERSHIP MESSAGE
# =========================

def membership_message(chat_id):

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "📢 عضویت در کانال",
            url=CHANNEL_LINK
        )
    )

    keyboard.add(
        types.InlineKeyboardButton(
            "✅ بررسی عضویت",
            callback_data="check_membership"
        )
    )

    bot.send_message(
        chat_id,
        """
❌ <b>برای استفاده از ربات ابتدا عضو کانال شوید.</b>

📢 ابتدا روی «عضویت در کانال» بزنید.

بعد از عضویت روی
«✅ بررسی عضویت» بزنید.

⚠️ تا قبل از تأیید عضویت،
هیچ امتیازی ثبت نمی‌شود.
""",
        reply_markup=keyboard
    )


# =========================
# REGISTER USER
# =========================

def register_user(user_id):

    cursor.execute("""
    SELECT registered, pending_referrer
    FROM users
    WHERE user_id = ?
    """, (user_id,))

    result = cursor.fetchone()

    if not result:
        return False, None

    registered = result[0]
    referrer_id = result[1]

    if registered == 1:
        return False, None

    if referrer_id == user_id:
        referrer_id = None

    # =========================
    # REFERRAL
    # =========================

    if referrer_id:

        cursor.execute("""
        SELECT user_id, registered
        FROM users
        WHERE user_id = ?
        """, (referrer_id,))

        referrer = cursor.fetchone()

        if referrer and referrer[1] == 1:

            cursor.execute("""
            UPDATE users
            SET points = 10,
                registered = 1,
                referred_by = ?,
                pending_referrer = NULL
            WHERE user_id = ?
            """, (
                referrer_id,
                user_id
            ))

            cursor.execute("""
            UPDATE users
            SET points = points + 10,
                invite_count = invite_count + 1
            WHERE user_id = ?
            """, (referrer_id,))

            conn.commit()

            cursor.execute("""
            SELECT points, invite_count
            FROM users
            WHERE user_id = ?
            """, (referrer_id,))

            info = cursor.fetchone()

            return True, (
                referrer_id,
                info[0],
                info[1]
            )

    # =========================
    # NORMAL REGISTRATION
    # =========================

    cursor.execute("""
    UPDATE users
    SET points = 5,
        registered = 1,
        pending_referrer = NULL
    WHERE user_id = ?
    """, (user_id,))

    conn.commit()

    return True, None


# =========================
# NOTIFY REFERRER
# =========================

def notify_referrer(
    referrer_id,
    new_user,
    points,
    invite_count
):

    username = (
        "@" + new_user.username
        if new_user.username
        else "ندارد"
    )

    text = f"""
🎉 <b>یک عضو جدید با لینک دعوت شما وارد شد!</b>

👤 نام: {new_user.full_name}

🆔 آیدی: {new_user.id}

🔹 یوزرنیم: {username}

⭐ <b>۱۰ امتیاز به حساب شما اضافه شد.</b>

💰 امتیاز فعلی: {points}

👥 معرفی موفق: {invite_count}
"""

    try:

        bot.send_message(
            referrer_id,
            text
        )

    except Exception as e:

        print("Notify error:", e)


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):

    user = message.from_user

    save_user(user)

    # دریافت معرف
    referrer_id = None

    parts = message.text.split()

    if len(parts) > 1:

        try:
            referrer_id = int(parts[1])

        except ValueError:
            referrer_id = None

    if referrer_id == user.id:
        referrer_id = None

    # ذخیره معرف
    if referrer_id:

        cursor.execute("""
        SELECT user_id, registered
        FROM users
        WHERE user_id = ?
        """, (referrer_id,))

        referrer = cursor.fetchone()

        if referrer:

            cursor.execute("""
            SELECT registered, pending_referrer
            FROM users
            WHERE user_id = ?
            """, (user.id,))

            current = cursor.fetchone()

            if current and current[0] == 0:

                cursor.execute("""
                UPDATE users
                SET pending_referrer = ?
                WHERE user_id = ?
                """, (
                    referrer_id,
                    user.id
                ))

                conn.commit()

    # بررسی کانال
    if not is_member(user.id):

        membership_message(
            message.chat.id
        )

        return

    # ثبت‌نام
    success, ref_info = register_user(
        user.id
    )

    if success:

        if ref_info:

            (
                referrer_id,
                ref_points,
                invite_count
            ) = ref_info

            notify_referrer(
                referrer_id,
                user,
                ref_points,
                invite_count
            )

            bot.send_message(
                message.chat.id,
                """
🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>

🔗 شما با لینک دعوت وارد شدید.

⭐ امتیاز شما: <b>۱۰</b>

🎁 معرف شما نیز <b>۱۰ امتیاز</b> گرفت.
"""
            )

        else:

            bot.send_message(
                message.chat.id,
                """
🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>

⭐ ۵ امتیاز به حساب شما اضافه شد.
"""
            )

    bot.send_message(
        message.chat.id,
        "🏠 <b>منوی اصلی:</b>",
        reply_markup=main_keyboard()
    )


# =========================
# CHECK MEMBERSHIP BUTTON
# =========================

@bot.callback_query_handler(
    func=lambda call:
    call.data == "check_membership"
)
def check_membership(call):

    user = call.from_user

    if not is_member(user.id):

        bot.answer_callback_query(
            call.id,
            "❌ هنوز عضو کانال نشده‌اید!",
            show_alert=True
        )

        return

    bot.answer_callback_query(
        call.id,
        "✅ عضویت تأیید شد!"
    )

    save_user(user)

    success, ref_info = register_user(
        user.id
    )

    if not success:

        bot.send_message(
            call.message.chat.id,
            "✅ شما قبلاً ثبت‌نام کرده‌اید.",
            reply_markup=main_keyboard()
        )

        return

    if ref_info:

        (
            referrer_id,
            ref_points,
            invite_count
        ) = ref_info

        notify_referrer(
            referrer_id,
            user,
            ref_points,
            invite_count
        )

        bot.send_message(
            call.message.chat.id,
            """
🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>

⭐ امتیاز شما: <b>۱۰</b>

🎁 معرف شما نیز <b>۱۰ امتیاز</b> گرفت.
"""
        )

    else:

        bot.send_message(
            call.message.chat.id,
            """
🎉 <b>ثبت‌نام با موفقیت انجام شد!</b>

⭐ امتیاز شما: <b>۵</b>
"""
        )

    bot.send_message(
        call.message.chat.id,
        "🏠 <b>منوی اصلی:</b>",
        reply_markup=main_keyboard()
    )


# =========================
# REGISTER BUTTON
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "📝 ثبت‌نام"
)
def registration(message):

    user = message.from_user

    save_user(user)

    if not is_member(user.id):

        membership_message(
            message.chat.id
        )

        return

    cursor.execute("""
    SELECT registered
    FROM users
    WHERE user_id = ?
    """, (user.id,))

    result = cursor.fetchone()

    if result and result[0] == 1:

        bot.send_message(
            message.chat.id,
            "✅ شما قبلاً ثبت‌نام کرده‌اید.",
            reply_markup=main_keyboard()
        )

        return

    success, ref_info = register_user(
        user.id
    )

    if success:

        if ref_info:

            (
                referrer_id,
                ref_points,
                invite_count
            ) = ref_info

            notify_referrer(
                referrer_id,
                user,
                ref_points,
                invite_count
            )

            bot.send_message(
                message.chat.id,
                """
🎉 <b>ثبت‌نام موفق بود!</b>

⭐ شما ۱۰ امتیاز گرفتید.

🎁 معرف شما هم ۱۰ امتیاز گرفت.
""",
                reply_markup=main_keyboard()
            )

        else:

            bot.send_message(
                message.chat.id,
                """
🎉 <b>ثبت‌نام موفق بود!</b>

⭐ ۵ امتیاز دریافت کردید.
""",
                reply_markup=main_keyboard()
            )


# =========================
# ACCOUNT
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "👤 حساب من"
)
def account(message):

    user = message.from_user

    save_user(user)

    cursor.execute("""
    SELECT points, invite_count, registered
    FROM users
    WHERE user_id = ?
    """, (user.id,))

    result = cursor.fetchone()

    points = result[0] if result else 0
    invite_count = result[1] if result else 0
    registered = result[2] if result else 0

    username = (
        "@" + user.username
        if user.username
        else "ندارد"
    )

    status = (
        "ثبت‌نام کرده"
        if registered
        else "ثبت‌نام نکرده"
    )

    text = f"""
👤 <b>حساب کاربری شما:</b>

🆔 آیدی عددی: <code>{user.id}</code>

👤 نام: {user.full_name}

🔹 یوزرنیم: {username}

⭐ امتیاز: <b>{points}</b>

📋 وضعیت ثبت‌نام: {status}

👥 تعداد معرفی موفق: <b>{invite_count}</b>
"""

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_keyboard()
    )


# =========================
# INVITE FRIENDS
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🎁 معرفی دوستان"
)
def invite_friends(message):

    user = message.from_user

    save_user(user)

    bot_info = bot.get_me()

    link = (
        f"https://t.me/"
        f"{bot_info.username}"
        f"?start={user.id}"
    )

    cursor.execute("""
    SELECT points, invite_count
    FROM users
    WHERE user_id = ?
    """, (user.id,))

    result = cursor.fetchone()

    points = result[0] if result else 0
    invite_count = result[1] if result else 0

    text = f"""
🎁 <b>معرفی دوستان</b>

دوستانت را با لینک اختصاصی خودت دعوت کن:

🔗 <code>{link}</code>

⭐ هر دعوت موفق:

➕ ۱۰ امتیاز برای شما

➕ ۱۰ امتیاز برای دوست شما

♾️ تعداد دعوت‌ها محدودیتی ندارد!

👥 معرفی موفق: <b>{invite_count}</b>

⭐ امتیاز فعلی: <b>{points}</b>
"""

    keyboard = types.InlineKeyboardMarkup()

    keyboard.add(
        types.InlineKeyboardButton(
            "📤 اشتراک‌گذاری لینک",
            url=(
                "https://t.me/share/url"
                f"?url={link}"
            )
        )
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=keyboard
    )


# =========================
# LOTTERY
# =========================

@bot.message_handler(
    func=lambda message:
    message.text == "🎟 قرعه‌کشی بزرگ استقلال"
)
def lottery(message):

    bot.send_message(
        message.chat.id,
        """
🎟 <b>قرعه‌کشی بزرگ استقلال 💙</b>

⭐ با دعوت دوستان امتیاز بیشتری جمع کن.

👥 هر دعوت موفق = ۱۰ امتیاز

♾️ تعداد دعوت‌ها نامحدود است.

💙 امیدواریم برنده خوش‌شانس قرعه‌کشی باشید!
""",
        reply_markup=main_keyboard()
    )


# =========================
# RUN
# =========================

print("🤖 ربات اجرا شد...")

bot.infinity_polling(
    skip_pending=True
)
