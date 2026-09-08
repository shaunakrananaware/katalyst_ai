from backend.eval.run_eval import fact_present


def test_numeric_facts_ignore_citations_and_substrings():
    assert not fact_present("3", "Security was approved [note-3-2].")
    assert not fact_present("3", "The pilot improved efficiency by 30 percent.")
    assert fact_present("3", "Only 3 closed-won deals are available.")
    assert fact_present("96000", "The final amount was $96,000 [lead-2].")
    assert fact_present("note-3-2", "Security was approved [note-3-2].")
