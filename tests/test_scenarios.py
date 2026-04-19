from eventforge import __doc__ as package_doc
from eventforge.scenarios import FLASH_CRASH_SCENARIO, get_default_scenario, list_sample_scenarios


def test_eventforge_package_docstring_reflects_game_factory_scope() -> None:
    assert package_doc == "Slice-of-life game factory package."


def test_flash_crash_is_registered_as_sample_content() -> None:
    samples = list_sample_scenarios()

    assert samples == (FLASH_CRASH_SCENARIO,)
    assert get_default_scenario() is samples[0]
