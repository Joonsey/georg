#!/bin/python3
import dataclasses
import datetime
import smtplib
import os

from typing import Optional
from pathlib import Path

import httpx
import supabase

@dataclasses.dataclass()
class Message:
    id: int
    messageId: int
    newsId: int
    title: str
    category: list
    markets: list[str]
    issuerId: int
    publishedTime: str
    correctionForMessageId: Optional[int] = None
    correctedByMessageId: Optional[int] = None
    issuerSign: Optional[str] = None
    issuerName: Optional[str] = None
    instrId: Optional[int] = None
    instrumentName: Optional[str] = None
    instrumentFullName: Optional[str] = None
    test: Optional[bool] = None
    numbAttachments: Optional[int] = None
    clientAnnouncementId: Optional[str] = None
    infoRequired: Optional[int] = None
    oamMandatory: Optional[int] = None

smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_username = os.environ.get("SMTP_USERNAME")
smtp_password = os.environ.get("SMTP_PASSWORD")

cache_name = datetime.datetime.today().strftime("%d_%m_%y")
cache_dir = "tmp"
cache_path = f"{cache_dir}/{cache_name}"

supabase_key = os.environ.get("SUPABASE_KEY") or ""
supabase_url = os.environ.get("SUPABASE_URL") or ""

client = supabase.create_client(
    supabase_key=supabase_key,
    supabase_url=supabase_url
)

def ensure_state():
    if not all([smtp_password, smtp_username]):
        raise ValueError("missing environment variables for SMPT_USERNAME or SMPT_PASSWORD.")

    if not all([supabase_key, supabase_url]):
        raise ValueError("missing environment variables for SUPABASE_KEY or SUPABASE_URL.")

    cache = Path(cache_path)
    if not cache.exists():
        cache.touch()

def load_already_checked_ids():
    with open(cache_path, "r") as cache:
        line = cache.readline()
        return list(filter(lambda x: x != "", line.split(" ")))

def get_daily_messages():
    # Their api is retarded, don't ask me why
    response = httpx.post("https://api3.oslo.oslobors.no/v1/newsreader/list?category=&issuer=&fromDate=&toDate=&market=&messageTitle=")
    json_messages = response.json()['data']['messages']

    return [Message(**m) for m in json_messages]

def add_id_to_cache(message_id: int):
    with open(cache_path, "a") as cache:
        cache.write(f"{message_id} ")


def send_email(email: str, title: str, content: str) -> None:
    assert smtp_username and smtp_password
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)

        message = f'Subject: {title}\n\n{content}'.encode() # We have to encode because ascii is incompatible with smtplib
        server.sendmail(smtp_username, email, message)

def get_message_content(message_id: int) -> tuple[str, str]:
    response = httpx.get(f"https://api3.oslo.oslobors.no/v1/newsreader/message?messageId={message_id}")

    json_messages = response.json()['data']['message']
    return json_messages['title'], json_messages['body']

def main():
    ensure_state()

    ids_checked_today = load_already_checked_ids()

    l = client.from_("emails").select("email, user_id, tickers (ticker_name)").execute()
    data = l.data

    messages = get_daily_messages()

    for row in data:
        user = row['email']
        user_id = row['user_id']
        tickers = [r['ticker_name'] for r in row['tickers']]

        if user_id in ids_checked_today:
            continue

        add_id_to_cache(user_id)

        for message in messages:
            if message.issuerSign and message.issuerSign in tickers:
                title, content = get_message_content(message.id)
                send_email(user, title, content)


main()
