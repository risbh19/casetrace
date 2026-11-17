import csv
import random
from datetime import date, timedelta
from pathlib import Path

TITLES = (
    "Customer support impersonation", "Fake investment advice", "Marketplace payment diversion",
    "Refund message impersonation", "Fictional QR payment dispute", "Misleading account verification",
)
SYNTHETIC_DIR = Path(__file__).resolve().parents[1] / "data" / "synthetic"
FIELDS = ["reference", "from_acc", "to_acc", "amount", "ts", "balance_remaining"]


def statement(case_number: int, opened_on: date) -> list[dict[str, str]]:
    rng = random.Random(case_number)
    initial = 32_000 + case_number * 3_500
    source = f"DEMO-{case_number:02}-V"
    rows = []
    for step in range(1, 6):
        destination = f"DEMO-{case_number:02}-{step:02}"
        amount = initial - step * rng.randint(600, 1200)
        rows.append(dict(zip(FIELDS, [
            f"DEMO-T{case_number:02}-{step:02}", source, destination,
            f"{amount}.00", f"{opened_on.isoformat()}T10:{step * 5:02}:00+05:30",
            f"{amount - 5000 if step == 5 else 0}.00",
        ], strict=True)))
        source = destination
    return rows


def fir(number: int, opened_on: date, title: str) -> str:
    shared = number in {1, 8, 15}
    phone = "90000 00001" if shared else f"90000 {number:05}"
    handle = "fictional01@demo" if shared else f"fictional{number:02}@demo"
    facts = f"INR {32_000 + number * 3500:,}.00 · +91 {phone} · UPI {handle} · IFSC DEMO0000001"
    name = f"Training witness {number:02}"
    if number % 2 == 0:
        return (
            f"केवल प्रशिक्षण हेतु · काल्पनिक शिकायत {number:02}\n"
            f"दिनांक: {opened_on.isoformat()}\nविषय: {title}\n"
            f"शिकायतकर्ता: {name}\nडिजिटल भुगतान का विवरण: {facts}\n"
        )
    return (
        f"TRAINING ONLY · Fictional FIR {number:02}\n"
        f"Date: {opened_on.isoformat()}\nSubject: {title}\n"
        f"Complainant: {name}\nReported payment details: {facts}\n"
    )


def generate(destination: Path, anchor: date) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for number in range(1, 25):
        opened_on = anchor - timedelta(days=number * 2)
        title = TITLES[(number - 1) % len(TITLES)]
        (destination / f"fir-{number:02}.txt").write_text(fir(number, opened_on, title), encoding="utf-8")
        if number <= 10:
            with (destination / f"bank-{number:02}.csv").open("w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=FIELDS)
                writer.writeheader()
                writer.writerows(statement(number, opened_on))
    with (destination / "calls.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["training_party", "peer", "seconds"])
        writer.writerows(("DEMO-HOTLINE", f"DEMO-PARTY-{number:02}", number * 17) for number in range(1, 13))


if __name__ == "__main__":
    generate(SYNTHETIC_DIR, date(2026, 10, 30))
