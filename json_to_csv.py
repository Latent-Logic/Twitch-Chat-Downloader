import re
import json
from pathlib import Path
import csv

from tcd.settings import argparser, settings

CSV_HEADER = ["time", "user", "target", "type", "amount"]

# "User1 gifted a Tier 1 sub to User2! They have given 123 Gift Subs in the channel!"
SUB_GIFT = re.compile(r"^(?P<src>.*) gifted a Tier (?P<tier>\d) sub to (?P<target>[^!]*)!.*$")
# "User1 subscribed with Prime. They've subscribed for 12 months! Message"
PRIME_SUB = re.compile(r"^(?P<src>.*) subscribed with Prime\..*$")
# "User1 subscribed at Tier 1. They've subscribed for 12 months! Message"
SUB = re.compile(r"^(?P<src>.*) subscribed at Tier (?P<tier>\d)\..*$")
# "AKLSJDLAKSJD User1 just cheered 1000 bits LandhorseHeart LandhorseHeart LandhorseHeart"
BITS = re.compile(
    r"^AKLSJDLAKSJD (?P<src>.*) just cheered (?P<amount>\d+) bits LandhorseHeart LandhorseHeart LandhorseHeart$"
)
# "User1 played Modem for 150 Bits"
SA = re.compile(r"^(?P<src>.*) played (?P<sound>.*) for (?P<amount>\d+) Bits$")
# "User1 just tipped $13.37 LandhorseHeart LandhorseHeart LandhorseHeart"
TIP = re.compile(
    r"^(?P<src>.*) just tipped \$(?P<amount>[\d.]+) LandhorseHeart LandhorseHeart LandhorseHeart$"
)


def json_to_csv(file: Path):
    json_blob = json.loads(file.read_text())
    csv_blob = []
    for i, line_blob in enumerate(json_blob["messages"]):
        text = line_blob["message"]
        match = SUB_GIFT.match(text)
        if match:
            csv_blob.append(
                (line_blob["ts"], line_blob["user"], match["target"], f"subs_t{match['tier']}", 1)
            )
        match = PRIME_SUB.match(text)
        if match:
            csv_blob.append((line_blob["ts"], match["src"], "", f"subs_t1", 1))
        match = SUB.match(text)
        if match:
            csv_blob.append((line_blob["ts"], match["src"], "", f"subs_t{match['tier']}", 1))
        match = BITS.match(text)
        if match:
            user, count = match["src"], match["amount"]
            for j in range(1, 10):
                other_blob = json_blob["messages"][i - j]
                if other_blob["user"].lower() == user.lower():
                    csv_blob.append((other_blob["ts"], user, "", "bits", count))
                    break
            else:
                raise ValueError(f"Couldn't find {count} bits in previous 10 messages from {text}")
        match = SA.match(text)
        if match:
            csv_blob.append((line_blob["ts"], match["src"], "", "bits", match["amount"]))
        match = TIP.match(text)
        if match:
            csv_blob.append((line_blob["ts"], match["src"], "", "tips", match["amount"]))
    with file.with_suffix(".csv").open("w") as f:
        csv_writer = csv.writer(f, delimiter=",")
        csv_writer.writerow(CSV_HEADER)
        csv_writer.writerows(csv_blob)


if __name__ == "__main__":
    args = argparser.parse_args()
    if not args.video:
        print("Please specify a video id")
        exit(1)
    json_to_csv(
        Path(
            settings["filename_format"].format(
                directory=settings["directory"], video_id=args.video, format="json"
            )
        )
    )
