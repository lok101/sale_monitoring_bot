from sale_monitoring_bot.env_bootstrap import load_project_env

load_project_env()

from sale_monitoring_bot.main import main  # noqa: E402

main()
