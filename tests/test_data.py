import pandas as pd
import pytest

from spendlens import data, sample_data


def test_generator_is_deterministic_for_a_seed():
    first = sample_data.generate(seed=7, months=6)
    second = sample_data.generate(seed=7, months=6)
    for left, right in zip(first, second):
        pd.testing.assert_frame_equal(left, right)


def test_generator_changes_with_the_seed():
    _, expenses_a, _ = sample_data.generate(seed=1, months=6)
    _, expenses_b, _ = sample_data.generate(seed=2, months=6)
    assert not expenses_a.equals(expenses_b)


def test_generated_files_load_through_the_loader(tmp_path):
    sample_data.write_sample_data(tmp_path, months=12)

    income = data.load_income(tmp_path)
    expenses = data.load_expenses(tmp_path)
    investments = data.load_investments(tmp_path)

    assert income["date"].dt.to_period("M").nunique() == 12
    assert expenses["date"].dt.to_period("M").nunique() == 12
    assert len(expenses) > 250
    assert "VOO" in set(investments["ticker"])
    assert (expenses["amount"] > 0).all()


def test_loader_reports_missing_columns(tmp_path):
    (tmp_path / "income.csv").write_text("date,amount\n2025-01-01,10\n")
    with pytest.raises(ValueError, match="missing column"):
        data.load_income(tmp_path)


def test_loader_points_to_the_generator_when_a_file_is_missing(tmp_path):
    with pytest.raises(FileNotFoundError, match="sample_data"):
        data.load_expenses(tmp_path)


def test_writer_refuses_to_overwrite_without_force(tmp_path):
    sample_data.write_sample_data(tmp_path, months=3)
    with pytest.raises(FileExistsError):
        sample_data.write_sample_data(tmp_path, months=3)
    sample_data.write_sample_data(tmp_path, months=3, force=True)


def test_env_var_overrides_the_data_folder(tmp_path, monkeypatch):
    monkeypatch.setenv(data.DATA_DIR_ENV, str(tmp_path))
    assert data.resolve_data_dir() == tmp_path


def test_private_folder_takes_priority_over_sample_data(tmp_path, monkeypatch):
    monkeypatch.delenv(data.DATA_DIR_ENV, raising=False)
    monkeypatch.setattr(data, "REPO_ROOT", tmp_path)
    assert data.resolve_data_dir() == tmp_path / "data"

    private = tmp_path / "data" / "private"
    private.mkdir(parents=True)
    (private / "expenses.csv").write_text("date,description,amount,category\n")
    assert data.resolve_data_dir() == private
