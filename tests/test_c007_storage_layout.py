"""C007 filesystem-path separation. Never touch real D:/ or user-profile data."""
from pathlib import Path
import sqlite3

import pytest

from nature_video_studio.storage_layout import (
    StorageLayout, UnsafeLayout, inspect_legacy_download_counts, trial_layout,
)


@pytest.fixture
def standard():
    return trial_layout(
        has_d_drive=True,
        user_profile=r"C:\Users\user",
        local_app_data=r"C:\Users\user\AppData\Local",
    )


def test_real_user_v1_locations_preserved_and_v2_distinct(standard):
    assert standard.v1_data == r"D:\NatureVideoStudio"
    assert standard.v1_app == r"D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2"
    assert standard.v2_app == r"D:\NVS_V2_Trial_App"
    assert standard.v2_data == r"D:\NatureVideoStudio_V2_Data"
    assert standard.v2_catalog == r"D:\NatureVideoStudio_V2_Data\catalog.sqlite3"
    assert standard.v2_media_folder == r"D:\NatureVideoStudio_V2_Data\downloads"
    assert standard.legacy_catalog == r"D:\NatureVideoStudio\library.sqlite3"


@pytest.mark.parametrize("app,data", [
    (r"D:\NatureVideoStudio", r"D:\NatureVideoStudio_V2_Data"),
    (r"D:\NatureVideoStudio\EXE", r"D:\NatureVideoStudio_V2_Data"),
    (r"D:\NVS_Recovery\C004_DB", r"D:\NatureVideoStudio_V2_Data"),
    (r"D:\NVS_V2_Trial_App", r"D:\NVS_V2_Trial_App\data"),
    (r"D:\NVS_V2_Trial_App", r"D:\NVS_V2_Trial_App"),
    (r"D:\NVS_V2_Trial_App", r"D:\NVS_Recovery\download"),
    (r"D:\03 자연풍경 비디오\NatureVideoStudio_V1_0_2", r"D:\NatureVideoStudio_V2_Data"),
    (r"D:\NVS_V2_Trial_App", r"D:\03 자연풍경 비디오"),
    (r"D:\NVS_V2_Trial_App", r"D:\NatureVideoStudio"),
])
def test_block_collisions_with_v1_backups_and_self(app, data, standard):
    unsafe = StorageLayout(
        v1_app=standard.v1_app, v1_data=standard.v1_data,
        recovery=standard.recovery, v2_app=app, v2_data=data)
    with pytest.raises(UnsafeLayout):
        unsafe.validate()


def test_case_insensitive_windows_aliases_blocked(standard):
    with pytest.raises(UnsafeLayout):
        StorageLayout(
            v1_app=standard.v1_app,
            v1_data=standard.v1_data,
            recovery=standard.recovery,
            v2_app=r"d:\naturevideostudio\BAD",
            v2_data=standard.v2_data,
        ).validate()


@pytest.mark.parametrize("bad", ["", r"D:relative", "relative", r"\\server\share\app", r"D:\\"])
def test_invalid_locations_fail_closed(bad, standard):
    with pytest.raises(UnsafeLayout):
        StorageLayout(
            v1_app=standard.v1_app, v1_data=standard.v1_data,
            recovery=standard.recovery, v2_app=bad, v2_data=standard.v2_data
        ).validate()


def test_drive_absent_fallback_no_overlap():
    layout = trial_layout(
        has_d_drive=False,
        user_profile=r"C:\Users\user",
        local_app_data=r"C:\Users\user\AppData\Local",
        videos_folder_exists=True,
    )
    assert layout.v1_data == r"C:\Users\user\Videos\NatureVideoStudio"
    assert layout.v2_data == r"C:\Users\user\Videos\NatureVideoStudio_V2_Data"
    assert layout.v2_app.startswith(r"C:\Users\user\AppData\Local\Programs")


def test_no_d_drive_fallback_without_videos_folder():
    layout = trial_layout(
        has_d_drive=False, user_profile=r"C:\Users\user",
        local_app_data=r"C:\Users\user\AppData\Local", videos_folder_exists=False)
    assert layout.v1_data == r"C:\Users\user\NatureVideoStudio"
    assert layout.v2_data == r"C:\Users\user\Videos\NatureVideoStudio_V2_Data"


def test_source_read_only_db_not_modified(tmp_path):
    database = tmp_path / "library.sqlite3"
    with sqlite3.connect(database) as c:
        c.execute("CREATE TABLE downloads (item_key TEXT)")
        c.execute("INSERT INTO downloads VALUES ('sample')")
    contents = database.read_bytes()
    assert inspect_legacy_download_counts(database) == 1
    assert database.read_bytes() == contents


def test_source_db_not_created_when_missing(tmp_path):
    database = tmp_path / "library.sqlite3"
    with pytest.raises(FileNotFoundError):
        inspect_legacy_download_counts(database)
    assert not database.exists()


def test_v2_settings_namespace_never_equals_v1():
    from nature_video_studio.storage_layout import (
        V2_SETTINGS_ORGANIZATION, V2_SETTINGS_APPLICATION,
    )
    assert (V2_SETTINGS_ORGANIZATION, V2_SETTINGS_APPLICATION) != (
        'NatureVideoStudio', 'NatureVideoStudio'
    )
