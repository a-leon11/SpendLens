import pandas as pd

from spendlens import anomalies, recurring, sample_data


def _expenses(rows):
    frame = pd.DataFrame(rows, columns=["date", "description", "amount", "category"])
    return frame.assign(date=pd.to_datetime(frame["date"]))


def test_finds_every_planted_one_off_with_no_false_alarms():
    sample = sample_data.generate()
    report = recurring.analyze_recurring(sample.expenses)

    flagged = anomalies.flag_anomalies(sample.expenses, exclude=report.items["description"])

    found = set(zip(flagged["date"], flagged["description"]))
    planted = set(sample_data.injected_anomalies())
    assert planted <= found          # recall: all of them
    assert len(flagged) == len(planted)  # precision: nothing else


def test_identical_history_makes_a_big_jump_an_outlier():
    rows = [(f"2024-01-{day:02d}", "Coffee", 50.0, "Food") for day in range(1, 11)]
    rows.append(("2024-02-01", "Mystery", 500.0, "Food"))

    flagged = anomalies.flag_anomalies(_expenses(rows))

    assert list(flagged["description"]) == ["Mystery"]
    assert flagged.iloc[0]["robust_z"] == 99.0  # capped, MAD was zero


def test_a_modest_increase_is_not_flagged():
    rows = [(f"2024-01-{day:02d}", "Coffee", 50.0, "Food") for day in range(1, 11)]
    rows.append(("2024-02-01", "Fancy coffee", 60.0, "Food"))  # statistically odd, practically nothing

    assert anomalies.flag_anomalies(_expenses(rows)).empty


def test_small_categories_are_compared_with_all_spending():
    rows = [(f"2024-01-{day:02d}", "Coffee", 50.0, "Food") for day in range(1, 11)]
    rows.append(("2024-02-01", "Flights", 5000.0, "Travel"))  # only one Travel transaction

    flagged = anomalies.flag_anomalies(_expenses(rows))

    assert list(flagged["description"]) == ["Flights"]
    assert flagged.iloc[0]["reference"] == "all spending"


def test_excluded_descriptions_are_ignored():
    rows = [(f"2024-01-{day:02d}", "Coffee", 50.0, "Food") for day in range(1, 11)]
    rows.append(("2024-02-01", "Mystery", 500.0, "Food"))

    assert anomalies.flag_anomalies(_expenses(rows), exclude=["Mystery"]).empty
