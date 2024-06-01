import dataclasses
import datetime
import smtplib
import os

from pathlib import Path

import httpx

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
    correctionForMessageId: int | None = None
    correctedByMessageId: int | None = None
    issuerSign: str | None = None
    issuerName: str | None = None
    instrId: int | None = None
    instrumentName: str | None = None
    instrumentFullName: str | None = None
    test: bool | None = None
    numbAttachments: int | None = None
    clientAnnouncementId: str | None = None
    infoRequired: int | None = None
    oamMandatory: int | None = None

smtp_server = 'smtp.gmail.com'
smtp_port = 587
smtp_username = os.environ.get("SMTP_USERNAME")
smtp_password = os.environ.get("SMTP_PASSWORD")

cache_name = datetime.datetime.today().strftime("%d_%m_%y")
cache_dir = "tmp"
cache_path = f"{cache_dir}/{cache_name}"

stocks_we_care_about = {
    "johannes.ronning@outlook.com": ["NAS", "NOM", "NONG"],
    "matiaskje@gmail.com": ["NAS", "NOM", "KOG"]
}

def ensure_state():

    if not all([smtp_password, smtp_username]):
        raise ValueError("missing environment variables for SMPT_USERNAME or SMPT_PASSWORD.")

    cache = Path(cache_path)
    if not cache.exists():
        cache.touch()

def load_already_checked_ids():
    with open(cache_path, "r") as cache:
        line = cache.readline()
        return [int(id) for id in list(filter(lambda x: x != "", line.split(" ")))]

def get_daily_messages():
    # Their api is retarded, don't ask me why
    response = httpx.post("https://api3.oslo.oslobors.no/v1/newsreader/list?category=&issuer=&fromDate=&toDate=&market=&messageTitle=")
    json_messages = response.json()['data']['messages']

    return [Message(**m) for m in json_messages]

def add_id_to_cache(message_id: int):
    with open(cache_path, "a") as cache:
        cache.write(f"{message_id} ")


def send_email(email: str, title: str, content: str) -> None:
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)

        message = 'Subject: {}\n\n{}'.format(title, content.encode()) # We have to encode because ascii is incompatible with smtplib
        server.sendmail(smtp_username, email, message)

def get_message_content(message_id: int) -> tuple[str, str]:
    response = httpx.get(f"https://api3.oslo.oslobors.no/v1/newsreader/message?messageId={message_id}")

    json_messages = response.json()['data']['message']
    return json_messages['title'], json_messages['body']

def main():
    ensure_state()

    ids_checked_today = load_already_checked_ids()

    for message in get_daily_messages():
        for user in stocks_we_care_about.keys():
            add_id_to_cache(message.id)

            if message.issuerSign and message.issuerSign in stocks_we_care_about[user] and message.id not in ids_checked_today:
                title, content = get_message_content(message.id)
                send_email(user, title, content)


main()
