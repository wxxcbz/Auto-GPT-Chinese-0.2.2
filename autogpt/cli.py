"""Main script for the autogpt package."""
import click


@click.group(invoke_without_command=True)
@click.option("-c", "--continuous", is_flag=True, help="启动持续模式")
@click.option(
    "--skip-reprompt",
    "-y",
    is_flag=True,
    help="跳过重新输入命令环节",
)
@click.option(
    "--ai-settings",
    "-C",
    help="指定使用哪个ai_settings.yaml文件, 同时自动跳过重新输入命令.",
)
@click.option(
    "-l",
    "--continuous-limit",
    type=int,
    help="定义持续模式中的持续次数",
)
@click.option("--speak", is_flag=True, help="开启语音模式")
@click.option("--debug", is_flag=True, help="开启Debug模式")
@click.option("--gpt3only", is_flag=True, help="开启GPT3.5模式")
@click.option("--gpt4only", is_flag=True, help="开启GPT4模式")
@click.option(
    "--use-memory",
    "-m",
    "memory_type",
    type=str,
    help="定义使用那种记忆后台",
)
@click.option(
    "-b",
    "--browser-name",
    help="指定使用哪个 Web 浏览器来使用 Selenium 抓取网络内容.",
)
@click.option(
    "--allow-downloads",
    is_flag=True,
    help="危险: 允许Auto-GPT自动下载文件.",
)
@click.option(
    "--skip-news",
    is_flag=True,
    help="指定是否在启动时不输出最新新闻.",
)
@click.option(
    # TODO: this is a hidden option for now, necessary for integration testing.
    #   We should make this public once we're ready to roll out agent specific workspaces.
    "--workspace-directory",
    "-w",
    type=click.Path(),
    hidden=True,
)
@click.option(
    "--install-plugin-deps",
    is_flag=True,
    help="为第三方插件安装外部依赖库.",
)
@click.pass_context
def main(
    ctx: click.Context,
    continuous: bool,
    continuous_limit: int,
    ai_settings: str,
    skip_reprompt: bool,
    speak: bool,
    debug: bool,
    gpt3only: bool,
    gpt4only: bool,
    memory_type: str,
    browser_name: str,
    allow_downloads: bool,
    skip_news: bool,
    workspace_directory: str,
    install_plugin_deps: bool,
) -> None:
    """
    Welcome to AutoGPT an experimental open-source application showcasing the capabilities of the GPT-4 pushing the boundaries of AI.

    Start an Auto-GPT assistant.
    """
    # Put imports inside function to avoid importing everything when starting the CLI
    from autogpt.main import run_auto_gpt

    if ctx.invoked_subcommand is None:
        run_auto_gpt(
            continuous,
            continuous_limit,
            ai_settings,
            skip_reprompt,
            speak,
            debug,
            gpt3only,
            gpt4only,
            memory_type,
            browser_name,
            allow_downloads,
            skip_news,
            workspace_directory,
            install_plugin_deps,
        )


if __name__ == "__main__":
    main()
