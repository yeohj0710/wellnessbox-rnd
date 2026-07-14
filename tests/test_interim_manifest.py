from wellnessbox_rnd.interim.manifest import APPROVED_SOURCE_ROOT, validate_interim_package

PACKAGE_ROOT = APPROVED_SOURCE_ROOT


def test_bundled_interim_package_manifest_and_split_counts_are_frozen() -> None:
    result = validate_interim_package(PACKAGE_ROOT)

    assert result.valid is True
    assert result.checked_files == 19
    assert result.failures == []
    assert result.split_counts == {
        "train": 120_000,
        "validation": 15_000,
        "calibration": 10_000,
        "blind_test": 5_000,
    }
    assert result.total_records == 150_000
    assert result.proxy_kpis_passed == 7
    assert result.proxy_kpis_total == 7
    assert result.manifest_sha256 == (
        "2a430ac5899544885d4be923213b50d526ffd0df016b2b34bf57a077d4c650a4"
    )
    assert result.model_sha256 == (
        "41786a4dabcdab36517d9991049621f26c217106dfb61004fede88f36a0a1aa4"
    )
