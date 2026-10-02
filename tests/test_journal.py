"""Tests de journal.py : modifier les repas de n'importe quel jour."""

import datetime

import pytest

from journal import add_entry, count_food, delete_entry, entries_for, remove_food, rename_food, replace_entry

DAY = datetime.date(2026, 9, 23)
OTHER_DAY = datetime.date(2026, 9, 24)


def test_entries_of_an_empty_day_are_empty_and_do_not_create_the_day():
    journal = {}
    assert entries_for(journal, DAY) == []
    assert journal == {}


def test_add_entry_goes_to_the_chosen_day_only():
    journal = {}
    add_entry(journal, DAY, "pomme", 150)
    add_entry(journal, DAY, "pain", 50)
    assert entries_for(journal, DAY) == [{"food": "pomme", "grams": 150}, {"food": "pain", "grams": 50}]
    assert entries_for(journal, OTHER_DAY) == []


def test_replace_entry():
    journal = {}
    add_entry(journal, DAY, "pomme", 150)
    replace_entry(journal, DAY, 0, "poire", 120)
    assert entries_for(journal, DAY) == [{"food": "poire", "grams": 120}]
    with pytest.raises(IndexError):
        replace_entry(journal, DAY, 3, "poire", 120)


def test_delete_last_entry_removes_the_day():
    journal = {}
    add_entry(journal, DAY, "pomme", 150)
    add_entry(journal, DAY, "pain", 50)
    delete_entry(journal, DAY, 0)
    assert entries_for(journal, DAY) == [{"food": "pain", "grams": 50}]
    delete_entry(journal, DAY, 0)
    assert journal == {}


def test_delete_missing_entry_does_nothing():
    journal = {}
    delete_entry(journal, DAY, 0)
    assert journal == {}


def test_count_rename_and_remove_a_food_across_days():
    journal = {}
    add_entry(journal, DAY, "Soupe", 300)
    add_entry(journal, DAY, "pain", 50)
    add_entry(journal, OTHER_DAY, "soupe", 200)
    assert count_food(journal, "SOUPE") == 2
    rename_food(journal, "soupe", "Velouté")
    assert [e["food"] for e in entries_for(journal, DAY)] == ["Velouté", "pain"]
    remove_food(journal, "velouté")
    assert journal == {DAY.isoformat(): [{"food": "pain", "grams": 50}]}
