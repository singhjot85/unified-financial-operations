from apps.core.app_setting import BaseSettings, RuntimeFlag


class CoreSettings(BaseSettings):

    class Meta:
        app = "core"

    GLOBAL_FIXTURE_DATA_PATH = RuntimeFlag(
        default="apps/fixture", data_type=str, help_text="Global fallback path which, houses all the fixture."
    )
    GLOBAL_SEED_DATA_PATH = RuntimeFlag(
        default="apps/fixture", data_type=str, help_text="Global fallback path which, houses all the seed data."
    )
