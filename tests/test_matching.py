import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from or_pricer.models import find_best_model_match


def make_models() -> list[dict]:
    return [
        {"id": "nopath:noslash", "pricing": {}},
        {"id": "bar/baz", "pricing": {}},
        {"id": "target/base:free", "pricing": {}},
        {"id": "target/base2", "pricing": {}},
        {"id": "target/other:batch", "pricing": {}},
    ]


def test_exact_match():
    models = make_models()
    assert find_best_model_match("bar/baz", models)["id"] == "bar/baz"


def test_alias_match():
    models = make_models()
    assert find_best_model_match("target/base2", models)["id"] == "target/base2"


def test_base_match_prefers_exact_base():
    models = make_models()
    assert find_best_model_match("target/base", models)["id"] == "target/base2"


def test_fuzzy_match_skips_noslash_ids():
    """Regression test for operator-precedence bug.

    Previously the conditional-expression parsing made any model id without a '/'
    match unconditionally, so 'nopath:noslash' would be returned for any query.
    """
    models = make_models()
    result = find_best_model_match("target/base", models)
    assert result is not None
    assert result["id"] != "nopath:noslash"
    assert result["id"].startswith("target/")


def test_fuzzy_match_skips_colon_variants():
    models = make_models()
    result = find_best_model_match("target/base", models)
    assert result["id"] != "target/base:free"
    assert result["id"] != "target/other:batch"


def test_no_match_returns_none():
    models = make_models()
    assert find_best_model_match("nonexistent/xyz", models) is None


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"PASS {name}")
    print("All tests passed.")
